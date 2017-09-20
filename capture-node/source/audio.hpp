
#ifdef WITH_PORTAUDIO

class AudioRecorder
{
public:
    AudioRecorder();
    ~AudioRecorder();

    void start(const char * wav_filename); // wav_filename is optional
    void stop();

    const short * get_raw_data(int& count);

private:
    struct AudioPrivate* p;
};

#endif // WITH_PORTAUDIO