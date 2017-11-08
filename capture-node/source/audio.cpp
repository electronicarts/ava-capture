// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#ifdef WITH_PORTAUDIO

#include "audio.hpp"

#include <stdio.h>
#include <malloc.h>
#include <portaudio.h>

#include <fstream>
#include <iostream>

#include <string>

typedef short SAMPLE;

#define NUM_CHANNELS       (2)
#define SAMPLES_PER_BUFFER (44100)
#define SAMPLE_RATE  	   (44100)
#define FRAMES_PER_BUFFER  (512)
#define PA_SAMPLE_TYPE     paInt16
#define SAMPLE_SILENCE     0

template<int sample_rate, int channels, typename sampleType>
class SimpleWavWriter
{
public:
    SimpleWavWriter() {}
    
    void open(const char * filename)
    {
        f.open(filename, std::ios::binary);

        // Write the file headers
        f << "RIFF----WAVEfmt "; // (chunk size to be filled in later)
        write_word( f, 16, 4 );  // no extension data
        write_word( f, 1, 2 );  // PCM - integer samples
        write_word( f, channels, 2 );  // two channels (stereo file)
        write_word( f, sample_rate, 4 );  // samples per second (Hz)
        write_word( f, channels*sample_rate*sizeof(sampleType), 4 );  // (Sample Rate * BitsPerSample * Channels) / 8
        write_word( f, 4, 2 );  // data block size (size of two integer samples, one for each channel, in bytes)
        write_word( f, sizeof(sampleType)*8, 2 );  // number of bits per sample (use a multiple of 8)

        // Write the data chunk header
        data_chunk_pos = f.tellp();
        f << "data----";  // (chunk size to be filled in later)        
    }
    ~SimpleWavWriter()
    {
        if (f.is_open())
            close();
    }
    void addFrame(int number_of_samples, const sampleType* buffer)
    {
        if (!f.is_open())
            return;

        //printf("Writing %d samples to the wav file\n", number_of_samples);

        for (int n = 0; n < number_of_samples; n++)
        {
            for (int c = 0 ; c < channels; c++)
            {
                write_word( f, (int)(buffer[n*channels + c]), sizeof(sampleType) );
            }
        }
    }
    void close()
    {
        // (We'll need the final file size to fix the chunk sizes above)
        size_t file_length = f.tellp();
  
        // Fix the data chunk header to contain the data size
        f.seekp( data_chunk_pos + 4 );
        write_word( f, file_length - data_chunk_pos + 8 );
    
        // Fix the file header to contain the proper RIFF chunk size, which is (file size - 8) bytes
        f.seekp( 0 + 4 );
        write_word( f, file_length - 8, 4 );
        
        f.close();
    }
protected:
    template <typename Word>
    std::ostream& write_word( std::ostream& outs, Word value, unsigned size = sizeof( Word ) )
    {
        // little endian
        for (; size; --size, value >>= 8)
            outs.put( static_cast <char> (value & 0xFF) );
        return outs;
    }    
private:
    std::ofstream f;
    size_t data_chunk_pos;
};

struct AudioRecordData
{
    AudioRecordData() : frameIndex(0), maxFrameIndex(0), totalRecordedSamples(0) {}

    SAMPLE        recordedSamples[SAMPLES_PER_BUFFER * NUM_CHANNELS];
    
    int           frameIndex;
    int           maxFrameIndex;
    unsigned long totalRecordedSamples;

    void flush()
    {
        if (frameIndex)
        {
            writer.addFrame(frameIndex, recordedSamples);
            frameIndex = 0;   
        }
    }

    SimpleWavWriter<SAMPLE_RATE, NUM_CHANNELS, SAMPLE>  writer;
};

struct AudioPrivate
{
    AudioPrivate() : err(paNoError), stream(0) {}

    PaStreamParameters  inputParameters;
    PaStream*           stream;
    PaError             err;

    AudioRecordData     data;

    int                 totalFrames;
    int                 numSamples;

    std::string         filename;
};

const short * AudioRecorder::get_raw_data(int& count)
{
    count = SAMPLES_PER_BUFFER;
    return p->data.recordedSamples;
}

static int recordCallback( const void *inputBuffer, void *outputBuffer,
                           unsigned long framesPerBuffer,
                           const PaStreamCallbackTimeInfo* timeInfo,
                           PaStreamCallbackFlags statusFlags,
                           void *userData )
 {
    AudioRecordData *data = (AudioRecordData*)userData;
    const SAMPLE *rptr = (const SAMPLE*)inputBuffer;
    
    unsigned long remainToCopy = framesPerBuffer;
    while (remainToCopy)
    {
        SAMPLE *wptr = &data->recordedSamples[data->frameIndex * NUM_CHANNELS];
        unsigned long toCopy = std::min(remainToCopy, static_cast<unsigned long>(data->maxFrameIndex - data->frameIndex));
       
        if( inputBuffer == NULL )
        {
            for(int i=0; i<toCopy; i++ )
            {
                *wptr++ = SAMPLE_SILENCE;  // left 
                if( NUM_CHANNELS == 2 ) *wptr++ = SAMPLE_SILENCE;  // right
            }
        }
        else
        {
            for(int i=0; i<toCopy; i++ )
            {
                *wptr++ = *rptr++;  // left 
                if( NUM_CHANNELS == 2 ) *wptr++ = *rptr++;  // right 
            }
        }

        data->frameIndex += toCopy;
        data->totalRecordedSamples += toCopy;
        remainToCopy -= toCopy;
        
        if (data->frameIndex >= data->maxFrameIndex)
            data->flush();
    }

    return paContinue;
}

AudioRecorder::AudioRecorder()
{
    p = new AudioPrivate();

    p->err = Pa_Initialize();
    if( p->err != paNoError ) 
    {
        fprintf(stderr, "Could not initialize PortAudio");
    }
}

AudioRecorder::~AudioRecorder()
{
    stop();
    delete p;
}

void AudioRecorder::start(const char * wav_filename)
{
    if (wav_filename)
    {
        p->data.writer.open(wav_filename);
        p->filename = wav_filename;
    }
    else
    {
        p->filename.clear();
    }

    p->data.maxFrameIndex = p->totalFrames = SAMPLES_PER_BUFFER;
    p->data.frameIndex = 0;
    p->data.totalRecordedSamples = 0;
    p->numSamples = p->totalFrames * NUM_CHANNELS;
    for(int i=0; i<p->numSamples; i++ ) p->data.recordedSamples[i] = 0;

    p->inputParameters.device = Pa_GetDefaultInputDevice();
    if (p->inputParameters.device == paNoDevice) {
        fprintf(stderr,"Error: No default input device.\n");
        return;
    }
    p->inputParameters.channelCount = NUM_CHANNELS;
    p->inputParameters.sampleFormat = PA_SAMPLE_TYPE;
    p->inputParameters.suggestedLatency = Pa_GetDeviceInfo( p->inputParameters.device )->defaultLowInputLatency;
    p->inputParameters.hostApiSpecificStreamInfo = NULL;

    p->err = Pa_OpenStream(
                &p->stream,
                &p->inputParameters,
                NULL,
                SAMPLE_RATE,
                FRAMES_PER_BUFFER,
                paClipOff,
                recordCallback,
                &p->data );
    if( p->err != paNoError ) 
        return;

    p->err = Pa_StartStream( p->stream );
    if( p->err != paNoError )
        return;

    if (wav_filename)
        printf("Start Recording Audio to %s\n", wav_filename);
    else
        printf("Start Streaming Audio\n");
}

void AudioRecorder::stop()
{
    if (!p->stream)
        return;

    printf("Stop Streaming Audio\n");

    p->err = Pa_StopStream( p->stream );
    if( p->err != paNoError ) 
        printf("Pa_StopStream Fail\n");

    p->err = Pa_CloseStream( p->stream );
    if( p->err != paNoError ) 
        printf("Pa_StopStream Fail\n");
    
    p->stream = 0;

    p->data.flush();
    p->data.writer.close();
}

void AudioRecorder::summarize(shared_json_doc summary)
{
	auto& a = summary->GetAllocator();

	rapidjson::Value root(rapidjson::kObjectType);
	root.AddMember("filename", rapidjson::Value(p->filename.c_str(), a), a);
	root.AddMember("channels", NUM_CHANNELS, a);
	root.AddMember("sample_rate", SAMPLE_RATE, a);
    root.AddMember("bits_per_sample", sizeof(SAMPLE)*8, a);
    root.AddMember("recorded_samples", p->data.totalRecordedSamples, a);
    root.AddMember("duration", p->data.totalRecordedSamples / (double)SAMPLE_RATE, a);
        
	summary->AddMember("audio", root, a);
}

const char * AudioRecorder::get_version()
{
    return Pa_GetVersionText();
}

#endif // WITH_PORTAUDIO        