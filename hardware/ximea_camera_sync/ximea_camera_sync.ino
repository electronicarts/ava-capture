// 
// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.
//
// Ximea Camera Sync Pulse
//
// Tested in: 
//     Arduino Mega 2560
//     Sparkfun Arduino Pro Micro 16MHz 5V
//

volatile int g_current_framerate = 0;

volatile int g_halves = 0;
volatile int g_thirds = 0;

volatile unsigned long g_duration_us = 1000;

#define PIN_EXTERNAL_SYNC 2
#define PIN_FIRST 3
#define PIN_LAST 53


void pulse_set_pins(int value, int first, int last)
{
  // Pins 2 to 49 are used for our pulse output
  for (int i=first;i<=last;i++)
    digitalWrite(i, value);
}

void emit_pulse()
{
   // Start of a pulse
  
    pulse_set_pins(HIGH,PIN_FIRST,45);

    if (g_halves==0)
      pulse_set_pins(HIGH,46,49);
    
    if (g_thirds==0)
      pulse_set_pins(HIGH,50,53);

    g_halves++;
    g_thirds++;

    if (g_halves>=2)
      g_halves = 0;
    if (g_thirds>=3)
      g_thirds = 0;

    // Use Timer3 for Pulse Duration
    TCCR3A = 0;
    TCCR3B = 0;
    TCNT3 = 0;
    OCR3B = g_duration_us*625/10000; // 16000000/256=62500 for example for 10ms 0.01*62500=625
    TCCR3B |= (1 << WGM12); // turn on CTC
    TCCR3B |= (1 << CS12); // 256 prescaler
    TCNT3 = 0;
    TIMSK3 = (1 << OCIE3B);
}

ISR(TIMER3_COMPB_vect)
{
  // End of a pulse
  TIMSK3 &= ~(1 << OCIE1A); // Disable Timer3 Interrupt
  pulse_set_pins(LOW,PIN_FIRST,PIN_LAST);
}

ISR(TIMER1_COMPA_vect)
{
  // Emit pulse from Timer1
  emit_pulse();
}

void ISR_external_pulse()
{
  static unsigned long last_interrupt_time = 0;
  unsigned long interrupt_time = millis();

  if (interrupt_time - last_interrupt_time >= 500/g_current_framerate) // allow up to 2x the selected framerate
  {
    // Emit pulse from external source
    emit_pulse();
  }
  last_interrupt_time = interrupt_time;
}

void start_pulse_external(unsigned long duration_us)
{
    g_halves = 0;
    g_thirds = 0;    
    g_duration_us = max(min(duration_us,1000000),100);
    attachInterrupt(digitalPinToInterrupt(PIN_EXTERNAL_SYNC), ISR_external_pulse, FALLING);
}

void start_pulse(int freq, unsigned long duration_us)
{
    if (freq>300)
      freq = 300;
    if (freq<1)
      freq = 1;
  
    noInterrupts(); // disable global interrupts
    
    g_halves = 0;
    g_thirds = 0;    

    // Set up Timer1 for the frequency of the pulse
    
    TCCR1A = 0;// set entire TCCR1A register to 0
    TCCR1B = 0;
    TCNT1 = 0;

    unsigned long val = F_CPU / (freq) - 1;
    if (val>65535)
    {
      // Using Timer1 CTC with a 1024 Prescaler
      OCR1A = ((val+1)/1024)-1; // compare and match value
      TCCR1B |= (1 << CS10)|(1 << CS12); // 1024 prescaler
    }
    else
    {
      // Using Timer1 CTC without a prescaler
      OCR1A = val; // compare and match value
      TCCR1B |= (1 << CS10); // Set CS10 bit so timer runs at clock speed (no prescaler)   
    }

    TCCR1B |= (1 << WGM12); // Turn on CTC mode:
    TCNT1 = 0;
    TIMSK1 = (1 << OCIE1A); // Enable timer compare interrupt 

    g_current_framerate = freq;
    g_duration_us = min(duration_us, (1000/freq-3)*1000);
    
    interrupts(); // enable global interrupts: 
}

void stop_pulse()
{    
    noInterrupts();
    
    TIMSK1 &= ~(1 << OCIE1A); // Disable Timer1 Interrupt

    detachInterrupt(digitalPinToInterrupt(PIN_EXTERNAL_SYNC));
    
    pulse_set_pins(LOW,PIN_FIRST,PIN_LAST);
    
    interrupts();
}

void setup() 
{
    pinMode(PIN_EXTERNAL_SYNC, INPUT_PULLUP);
    for (int i=PIN_FIRST;i<=PIN_LAST;i++)
      pinMode(i, OUTPUT);

    Serial.begin(115200);
    while (!Serial) {
      ; // wait for serial port to connect. Needed for native USB
    }
}

unsigned char blocking_read()
{
  while (Serial.available()==0) 
    ;
  return Serial.read();
}

void loop() 
{
  if (Serial.available()>0)
  {
     int c = Serial.read();
     switch (c)
     {
     case 'I': // identify the device
       Serial.write("OK");
       break;
     case 'F': // query the current framerate and pulse duration
     {
       Serial.write(g_current_framerate/255);
       Serial.write(g_current_framerate%255);
       Serial.write(g_duration_us/255);
       Serial.write(g_duration_us%255);
       break;
     }
     case 'E': // Start external sync
     case 'S': // start pulses at the specified framerate, for the specified duration
     {
       unsigned char byte1 = blocking_read();
       unsigned char byte2 = blocking_read();
       int new_framerate = byte1*255+byte2;
       byte1 = blocking_read();
       byte2 = blocking_read();
       int new_duration = byte1*255+byte2;
       stop_pulse();
       delay(20);
       if (c=='E')
        start_pulse_external(new_duration);
       else
        start_pulse(new_framerate, new_duration);
       Serial.write("OK");
       break;
     }
     case 'X': // stop pulses
       stop_pulse();
       Serial.write("OK");
       break;
     }
  }
}





