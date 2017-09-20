
#ifdef WITH_PORTAUDIO

#include "json.hpp"

class AudioRecorder
{
public:
    AudioRecorder();
    ~AudioRecorder();

    void start(const char * wav_filename); // wav_filename is optional
    void stop();

    void summarize(shared_json_doc summary);

    const short * get_raw_data(int& count);

    static const char * get_version();

private:
    struct AudioPrivate* p;
};

#endif // WITH_PORTAUDIO