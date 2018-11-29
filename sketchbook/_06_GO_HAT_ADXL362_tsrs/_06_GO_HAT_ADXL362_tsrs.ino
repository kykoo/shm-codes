//
// GPS-OCXO-HAT System for ADXL362
//
//
//
// ?Written by K.Y. KOO (k.y.koo@exeter.ac.uk)
//
// ?Version 0.1, 17 Oct 2017 
//
//
//

#define NPPS_SKIPPING 3

//-------------------------------------------------------------------------------------------------
// HEADERS
//-------------------------------------------------------------------------------------------------

//
// HEADERS FOR GPS
//
#include <Arduino.h>
#include <Adafruit_GPS_hw.h>
#include <Time.h>
#define GOM_DEBUG
//#include <stdio.h>
//#include <string.h>

//
// HEADERS FOR ADXL362
//
#include <stdint.h>
#include <SPI.h>
#include <ADXL362.h>
#define SENSITIVITY 0.004

Adafruit_GPS GPS(&Serial3);
boolean usingInterrupt = false;
void useInterrupt(boolean); // Func prototype keeps Arduino 0023 happy
// Definition for Timer
volatile unsigned long count_timer1_H = 0L; // number of overflow of timer1
volatile unsigned int  count_timer1_L = 0;  // clock-count of timer1
volatile unsigned long count_PPS_H    = 0L;  // clock-count for PPS (higher 32bit)
volatile unsigned int  count_PPS_L    = 0;   // clock-count for PPS (lower  16bit)
volatile boolean newPPS = false;
volatile time_t time_gps = 0;
unsigned long count_DAQ_0_H  = 0L;  // clock-count for DAQ (higher 32bit)
unsigned int  count_DAQ_0_L  = 0;   // clock-count for DAQ (lower  16bit)
unsigned long count_DAQ_1_H  = 0L;  // clock-count for DAQ (higher 32bit)
unsigned int  count_DAQ_1_L  = 0;   // clock-count for DAQ (lower  16bit)
unsigned int npps = 0;
boolean GPSECHO = false;
unsigned long count_NMEA_PARSING_H = 0L; // Clock-count for NMEA Parsing (higher 32bit)
unsigned int  count_NMEA_PARSING_L = 0;  // Clock-count for NMEA Parsing (lower  16bit)
//
// VARIABLES FOR ADXL362
//
ADXL362 xl;
int16_t temp;
int16_t XValue, YValue, ZValue;
boolean firstReading = true;
boolean ADXL362_started = false;

//
// VARIABLES FOR SWITCH
//
typedef struct
{
	int ButtonNumber;
	int ReadingNow;
	int ReadingPrev;
	long timeDetected;
	boolean isPressed;
} button;

button buttons[2];


//
// VARIABLES FOR INTEGRATION
//
int state = 0;      // the current state of the output pin


char buff[80];
char buff_H[11];
char buff_L[6];
char buff_x[8];
char buff_y[8];
char buff_z[8];

int statusLED_PIN = 13;
int statusLED = 0;
unsigned int countExec = 0;


//
// FUNCTIONS FOR GPS
//

SIGNAL(TIMER0_COMPA_vect) {
	char c = GPS.read();
#ifdef UDR0
	if (GPSECHO)
		if (c) UDR0 = c;  
#endif
}

// INTERRUPT FOR GPS RECEIVER
void useInterrupt(boolean v) {
	if (v) {
		OCR0A = 0xAF;  // 1.024 msec for 16 MHz
		OCR0A = 0x6E;  // 1.024 msec for 10 MHz
		TIMSK0 |= _BV(OCIE0A);
		usingInterrupt = true;
	} 
	else {
		TIMSK0 &= ~_BV(OCIE0A);
		usingInterrupt = false;
	}
}

// TIMER1 OVERFLOW COUNTER
ISR(TIMER1_OVF_vect)   
{  
	count_timer1_H++;
}

// TIMER FOR CAPTURING PPS
ISR(TIMER1_CAPT_vect)   
{ 
	count_timer1_L = ICR1;
	if(  (bitRead(TIFR1,TOV1)==1) && (count_timer1_L < 32768 ) ){
		// The rare special case when count_timer1_H hasn't been updated yet
		count_PPS_H = count_timer1_H + 1;
		count_PPS_L = count_timer1_L;
	}else{
		// The Usual case
		count_PPS_H = count_timer1_H;
		count_PPS_L = count_timer1_L;
	}
	newPPS = true;
}

void ADXL362_begin(){
	xl.begin(53);                   // Setup SPI protocol, issue device soft reset
	xl.beginMeasure();              // Switch ADXL362 to measure mode  
	Serial.println("0,ADXL362: Start Measuring...");
   
}

boolean isValidPPS(){
	// Check if a PPS has exact time information available
	// obtained by parsing NMEA sentences about 0.5sec before the PPS
	//
	//Serial.print("0,PPS,");
	//Serial.println(count_PPS_H - count_NMEA_PARSING_H);
	// 0.6144 sec ago
	if(count_PPS_H - count_NMEA_PARSING_H < F_CPU/160000*1.5){
		return true;
	}else{
		return false;
	}

	/*
	  if( dCC < 8e6 ){
	  Serial.print("0,Valid PPS,");
	  Serial.print(dCC);
	  return true;
	  }else{<
	  Serial.print("0,Invalid PPS,");
	  Serial.print(dCC);
	  return false;
	  }
	*/
}

void setup()
{
	for(int i=0; i<2; i++){
		buttons[i].ReadingNow = HIGH;
		buttons[i].ReadingPrev = HIGH;
		buttons[i].timeDetected = 0L;
		buttons[i].isPressed = false;
	}

	delay(1000);
	//
	// setup for ADC 
	//
	Serial.begin(115200);         // Initialize the serial port to the PC
	Serial.println(F("0,Wireless DAQ System v1.0..."));
 	Serial.println(F("0,- Configuring DAQ system..."));

	//
	// SETUP FOR GPS
	//
	GPS.begin(9600);
	Serial.print(F("0,- Configuring GPS module. ..\n"));
	Serial.print(F("0,-- Sending initialise command to GPS..."));
	useInterrupt(true);
	GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);
	GPS.sendCommand(PMTK_SET_NMEA_UPDATE_1HZ);   // 1 Hz update rate
	Serial.println(F("done."));
	// TIMER1 CONFIGURATION: THE MAIN CLOCK COUNTS
	Serial.println(F("0,-- Starting Timer1 with OVF/CAPTURE interrupts"));
	TCCR1A = 0;    // No Compare Output, No waveform
	TCCR1B = _BV(ICNC1) | _BV(ICES1) | _BV(CS10 );
	// ICNC = Input Capture Noise Canceller, 
	// ICES = Input Capture Edge Select (raising edige)
	TCCR1C = 0;  // Force Output Compare for A/B; all disabled
	TCNT1  = 0;  // Timer Counter
	TIMSK1 = _BV(ICIE1) | _BV(TOIE1);   // Start Timer
	// ICIE = Input Capture Interrupt Enabled
	// TOIE = Overflow Interrupt Enable
	// TOIE1 = No prescaling
	Serial.println(F("0,- Configuration all done."));
	//
	// Reading time-source from GPS
	//
	Serial.println(F("0, Waiting for PPS signals..."));
	while(npps < NPPS_SKIPPING){
		if(newPPS==true){
			newPPS = false;
			npps++;
			Serial.print("0,- Skipping PPS: (");
			Serial.print(npps);
			Serial.print("/");
			Serial.print(NPPS_SKIPPING);
			Serial.println(")");
		}
	}
	Serial.println("0,- done!");
	//
	// NMEA Processing
	//
	Serial.println("0,Parsing NMEA sentences...");
	while(npps < NPPS_SKIPPING+2){
		if (GPS.newNMEAreceived()) {
			if (!GPS.parse(GPS.lastNMEA())){ 
				Serial.println(F("0,- GPS.parse(GPS.lastNMEA()) failed..."));
			}
			else{
				tmElements_t tm;
				tm.Year   = GPS.year + 30; // 2000-1970
				tm.Month  = GPS.month;
				tm.Day    = GPS.day;
				tm.Hour   = GPS.hour;
				tm.Minute = GPS.minute;
				tm.Second = GPS.seconds;
				time_gps = makeTime(tm);
				//  useInterrupt(false);
				Serial.print(F("0,- NMEA parsed: "));
				Serial.print(GPS.hour); 
				Serial.print(F(":"));
				Serial.print(GPS.minute); 
				Serial.print(F(":"));
				Serial.print(GPS.seconds); 
				Serial.print(F("."));
				Serial.print(GPS.milliseconds);
				Serial.print(F(", "));
				Serial.print(GPS.day, DEC); 
				Serial.print(F("/"));
				Serial.print(GPS.month, DEC); 
				Serial.print(F("/20"));
				Serial.println(GPS.year, DEC);

			}
		}
		if(newPPS==true){
			newPPS = false;
			npps++;
		}
	}
	Serial.println("0,- done!");
	delay(100); 

	//
	// SETUP FOR ADXL362
	//

	//
	// SETUP FOR BUTTONS
	//
	buttons[0].ButtonNumber = A3;
	buttons[1].ButtonNumber = A4;
	for(int i=0; i<2; i++){
		pinMode(buttons[i].ButtonNumber,INPUT);
	}

    // StatusLED
	pinMode(statusLED_PIN,OUTPUT);
    
	//
	// OPERATION MODE
	//
	state = 1;

    
}


//--------------------------------------------------------
//        STATES OF MACHINE
//
//						   useInterrupt Serial3  ADXL362
// state 1: PPS	   mode	   true			 working   dead
// state 2: Silent mode	   false		 dead	   dead
// state 3: DAQ	   mode	   false		 dead	  working

void stateTransition(int cmd){
     
	if( state == 1 && cmd == 117  ){

        // STATE=1 TO STATE=2: PPS-MODE TO SILENT-MODE
        
        useInterrupt(false);		// useInterrupt
        Serial3.end();				// Serial3 
        TIMSK1 &= ~(_BV(ICIE1)); 	// Disable PPS-Interrupt
                                    // ADXL362
        state = 2;
        Serial.println("0,state=2");
        
    }else if(state==2 && cmd == 117){

        // STATE=2 TO STATE=3: SILENT-MODE TO DAQ MODE

        TIMSK1 |= _BV(ICIE1); 		// Enable PPS-Interrupt
        ADXL362_begin();  			// ADXL362
        
        firstReading = true;
        state = 3;
        Serial.println("0,state=3");
        Serial.flush();
        delay(1000);
        
    }else if(state==3 && cmd == 117){

        // STATE=3: DO NOTHING
        
        Serial.println("0,state=3");
        
    }else if(state == 3 && cmd == 100){

        // STATE=3 TO STATE 2: DAQ-MODE TO SLIENT MODE
        
        TIMSK1 &= ~(_BV(ICIE1)); // Disable PPS-Interrupt
        
        state = 2;
        Serial.println("");
        Serial.println("0,state=2");
            
    }else if(state ==2 && cmd == 100){
        
        // STATE=2 TO SATE 1: SILENT-MODE TO PPS-MODE
        
        Serial3.begin(9600);   	// Serial3
        useInterrupt(true);		// useInterrupt
        TIMSK1 |= _BV(ICIE1); 	// Enable PPS-Interrupt
        
        newPPS = false;
        state = 1;
        Serial.println("0,state=1");
            
    }else if(state ==1 && cmd == 100){

        // STATE=1: DO NOTHING

        Serial.println("0,state=1");
    }
    return;
}


//
// STATE OPERATION
//

void stateOperation(){
        
	//
	// PPS-MODE OPERATION
	//
    
	if(state == 1){
		// Parsing NMEA
		if (GPS.newNMEAreceived()) {
			if (!GPS.parse(GPS.lastNMEA())){
				Serial.println(F("0,-- GPS.parse(GPS.lastNMEA()) failed..."));
			}else{
				tmElements_t tm;
				tm.Year   = GPS.year + 30; // 2000-1970
				tm.Month  = GPS.month;
				tm.Day    = GPS.day;
				tm.Hour   = GPS.hour;
				tm.Minute = GPS.minute;
				tm.Second = GPS.seconds;
				time_gps = makeTime(tm);
				// Read the clock-count
				noInterrupts();
				count_NMEA_PARSING_H = count_timer1_H;
				count_NMEA_PARSING_L = TCNT1;
				interrupts();
			}
		}
		// outputs time and clock-counts of pps
		if(newPPS && isValidPPS()){
			Serial.print("1,");
			Serial.print(count_PPS_H);
			Serial.print(",");
			Serial.print(count_PPS_L);
			Serial.print(",");
			Serial.println(time_gps+1);
		}
		newPPS = false;
	}

    
	//
	// SILET-MODE OPERATIONS
	//
    
	if(state==2){
		delay(100);
		newPPS = false;
	}

    
	//
	// DAQ-MODE OPERATIONS
	//
    
	if(state==3){

		// outputs time and clock-counts of pps
		if(newPPS){
			Serial.print("3,");
			Serial.print(count_PPS_H);
			Serial.print(",");
			Serial.println(count_PPS_L);
            newPPS = false;
		}
		
		if(xl.dataReadyTimeout()==1){
			Serial.println("0,Data Ready Timeout");
			Serial.println("0,Restarting ADXL362");
            Serial.flush();
            delay(1000);
                
			ADXL362_begin();
			firstReading = true;
			return;
		}
		xl.readXYZData(XValue, YValue, ZValue);

		// Read the clock-count
		noInterrupts();
		count_DAQ_1_H = count_timer1_H;
		count_DAQ_1_L = TCNT1;
		interrupts();

		if(firstReading){
			// If First Reading, discard it.
			firstReading = false;
		}else{
			// NEW CODE: Fixed width for measured values
			sprintf(buff_H,"%10lu",count_DAQ_0_H);
			sprintf(buff_L,"%5u",  count_DAQ_0_L);
			strcpy(buff, "2,");
			strcat(buff,buff_H);
			strcat(buff,",");
			strcat(buff,buff_L);
			strcat(buff,",");
			Serial.print(buff);
			if(XValue >= 0.0)
				Serial.print(" ");
			Serial.print((float)XValue *SENSITIVITY,4);
			Serial.print(",");
			if(YValue >= 0.0)
				Serial.print(" ");
			Serial.print((float)YValue *SENSITIVITY,4);
			Serial.print(",");
			if(ZValue >= 0.0)
				Serial.print(" ");
			Serial.println((float)ZValue *SENSITIVITY,4);
		}
		count_DAQ_0_H = count_DAQ_1_H;
		count_DAQ_0_L = count_DAQ_1_L;
	}
}

void toggleLED(){
    if(statusLED ==0){
        digitalWrite(statusLED_PIN,HIGH);
        statusLED = 1;
    }else{
        digitalWrite(statusLED_PIN,LOW);
        statusLED = 0;
    }
    return;
}

void loop()
{
	// ACCEPTING COMMANDS THROUGH SERIAL
	int cmd = 0;
	if(Serial.available() > 0)
        cmd = Serial.read();

    // STATE TRANSITION ROUTINE
    stateTransition(cmd);

    // STATE OPERATION ROUTINES
    stateOperation();

    // STATUS-LED
    countExec++;
    if(countExec>10){
        toggleLED();
        countExec = 0;
    }
}
