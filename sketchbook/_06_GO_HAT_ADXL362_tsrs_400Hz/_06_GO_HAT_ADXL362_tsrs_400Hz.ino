//
// GPS-OCXO-HAT for ADXL362
// - 400Hz sampling version
//
//
// Written by K.Y. KOO (k.y.koo@exeter.ac.uk)
//
// Version  0.2, 29 Nov 2018
//			0.1, 17 Oct 2017 
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

//
// HEADERS FOR ADXL362
//
#include <stdint.h>
#include <SPI.h>
#include <ADXL362.h>

Adafruit_GPS GPS(&Serial3);
boolean usingInterrupt = false;
void useInterrupt(boolean); // Func prototype keeps Arduino 0023 happy


// CC of Timer1
volatile unsigned long count_timer1_H = 0L; // number of overflow of timer1 (32bit)
volatile unsigned int  count_timer1_L = 0;  // clock-count of timer1        (16bit)
// CC of PPS
volatile unsigned long count_PPS_H    = 0L;  // clock-count for PPS (higher 32bit)
volatile unsigned int  count_PPS_L    = 0;   // clock-count for PPS (lower  16bit)
// CC of DAQ
unsigned long count_DAQ_H  = 0L;  // clock-count for DAQ (higher 32bit)
unsigned int  count_DAQ_L  = 0;   // clock-count for DAQ (lower  16bit)
// Exact Time
volatile time_t time_gps = 0;


volatile boolean newPPS_Flag = false;

// CC of NMEA_PARSING
unsigned long count_NMEA_PARSING_H = 0L; // Clock-count for NMEA Parsing (higher 32bit)
unsigned int  count_NMEA_PARSING_L = 0;  // Clock-count for NMEA Parsing (lower  16bit)

unsigned int npps = 0;
boolean GPSECHO = false;

//
// VARIABLES FOR ADXL362
//
ADXL362 xl;
int16_t temp;
int16_t XValue, YValue, ZValue;
boolean valid_data_Ready = false;  // The first reading from ADXL362 needs to be discarded.
boolean ADXL362_started = false;



//
// VARIABLES FOR INTEGRATION
//
int state = 0;      // the current state of the output pin


char buff[80];
char buff_H[11];
char buff_L[6];

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
	newPPS_Flag = true;
}

boolean isValidPPS(){
	// Check if a PPS is within 0.6144 sec from the most recent NMEA sentence
	//
	//Serial.print("0,PPS,");
	//Serial.println(count_PPS_H - count_NMEA_PARSING_H);
	// 0.6144 sec ago
	if(count_PPS_H - count_NMEA_PARSING_H < F_CPU/160000*1.5){
		return true;
	}else{
		return false;
	}
}

void ADXL362_begin(){
	xl.begin(53);                   // Setup SPI protocol, issue device soft reset
	xl.beginMeasure();              // Switch ADXL362 to measure mode  
	Serial.println("0,ADXL362: Start Measuring...");
   
}

void setup()
{    
	Serial.begin(115200);         // Initialize the serial port to the PC
	Serial.println(F("0,Wireless DAQ System v1.0..."));
 	Serial.println(F("0,- Configuring DAQ system..."));

	//
	// SETUP FOR GPS
	//

    GPS.begin(9600);

    Serial.print(F("0,- Configuring GPS module...\n"));
	Serial.print(F("0,-- Sending initialise command to GPS..."));
	useInterrupt(true);

	GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);
	GPS.sendCommand(PMTK_SET_NMEA_UPDATE_1HZ);   // 1 Hz update rate

    Serial.println(F("done."));

    //
	// TIMER1 CONFIGURATION: THE MAIN CLOCK COUNTER
    //

    Serial.println(F("0,-- Starting Timer1 with OVF/CAPTURE interrupts..."));

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
		if(newPPS_Flag==true){
			newPPS_Flag = false;
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
		if(newPPS_Flag==true){
			newPPS_Flag = false;
			npps++;
		}
	}
	Serial.println("0,- done!");
	delay(100); 


    // StatusLED
	pinMode(statusLED_PIN,OUTPUT);
    
	// STATE OF MACHINE
	state = 1;
    
}


//--------------------------------------------------------
// STATES OF MACHINE: the same with the python code
//
//						   useInterrupt Serial3  ADXL362
// state 1: PPS	   mode	   true			 working   dead
// state 2: Silent mode	   false		 dead	   dead
// state 3: DAQ	   mode	   false		 dead	  working
// state 4: DAQ	   mode	   false		 dead	  working
// state 5: DAQ	   mode	   false		 dead	  working

void stateTransition(int cmd){

    // Increasing or Decreasing State Number:
    // cmd = 'u' (117) for up
    // cmd = 'd' (100) for down
    
    if (cmd == 117){
        if( state == 1 ){

            // STATE=1 TO STATE=2
            // PPS-MODE TO SILENT-MODE

            useInterrupt(false);		// useInterrupt
            Serial3.end();				// Serial3 
            TIMSK1 &= ~(_BV(ICIE1)); 	// Disable PPS-Interrupt
            // ADXL362
            state = 2;
        
        }else if(state==2){

            // STATE=2 TO STATE=3
            // SILENT-MODE TO DAQ MODE

            TIMSK1 |= _BV(ICIE1); 		// Enable PPS-Interrupt
            ADXL362_begin();  			// ADXL362
            
            valid_data_Ready = false;
            state = 3;

            Serial.flush();
            delay(1000);
       
        }else if(state==3 | state ==4){
            // STATE 3 TO STATE 4 OR
            // STATE 4 TP STATE 5
            state++;
        }else if(state==5){
            // STATE=3
            // DO NOTHING
        }
        
        Serial.print("0,state=");
        Serial.println(state);
            
    }else if( cmd == 100){
        if(state == 5 | state ==4){
            // STATE 5 TO STATE 4 OR
            // STATE 4 TP STATE 3
            state--;
        }else if(state == 3 ){

            // STATE=3 TO STATE 2
            // DAQ-MODE TO SLIENT MODE
        
            TIMSK1 &= ~(_BV(ICIE1)); // Disable PPS-Interrupt
        
            state = 2;
            
        }else if(state ==2 ){
        
            // STATE=2 TO SATE 1
            // SILENT-MODE TO PPS-MODE
        
            Serial3.begin(9600);   	// Serial3
            useInterrupt(true);		// useInterrupt
            TIMSK1 |= _BV(ICIE1); 	// Enable PPS-Interrupt
        
            newPPS_Flag = false;
            state = 1;
            
        }else if(state ==1 ){

            // State=1: DO NOTHING
        }
        Serial.print("0,state=");
        Serial.println(state);
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
		if(newPPS_Flag && isValidPPS()){
			Serial.print("1,");
			Serial.print(count_PPS_H);
			Serial.print(",");
			Serial.print(count_PPS_L);
			Serial.print(",");
			Serial.println(time_gps+1);
		}

		newPPS_Flag = false;
	}

    
	//
	// SILET-MODE OPERATIONS
	//
    
	if(state==2){
		delay(100);
		newPPS_Flag = false;
	}

    
	//
	// DAQ-MODE OPERATIONS
	//
    
	if(state==3 | state==4 | state==5){

		// OUTPUTS CLOCK-COUNTS OF PPS
		if(newPPS_Flag){
			Serial.print("3,");
			Serial.print(count_PPS_H);
			Serial.print(",");
			Serial.println(count_PPS_L);
            newPPS_Flag = false;
		}

        // READ FROM ADXL362
		if(xl.dataReadyTimeout()==0){
            xl.readXYZData(XValue, YValue, ZValue);            
        }else{
            // RESET ADXL362
			Serial.println("0,Data Ready Timeout");
			Serial.println("0,Restarting ADXL362");
                
			ADXL362_begin();
			valid_data_Ready = false;
            
            Serial.flush();
            delay(1000);

			return;
		}

		// READ THE CLOCK-COUNT OF DAQ
		noInterrupts();
		count_DAQ_H = count_timer1_H;
		count_DAQ_L = TCNT1;
		interrupts();

        // PRINT OUT MEASUREMENTS
		if(valid_data_Ready){
            // V3 CODE
            unsigned char msgID = 50;
            Serial.write((byte *)&msgID,1);
            Serial.write((byte *)&count_DAQ_H,4);
            Serial.write((byte *)&count_DAQ_L,2);
            Serial.write((byte *)&XValue,2);
            Serial.write((byte *)&YValue,2);
            Serial.write((byte *)&ZValue,2);
            Serial.write("\r\n");
		}else{
            // Discard the first reading
			valid_data_Ready = true;
		}
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
	// ACCEPTING COMMANDS VIA SERIAL
	int cmd = 0;
	if(Serial.available() > 0)
        cmd = Serial.read();

    // STATE TRANSITION ROUTINES
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



// // V2 CODE: Fixed width for measured values
// sprintf(buff_H,"%10lu",count_DAQ_H);
// sprintf(buff_L,"%5u",  count_DAQ_L);
// strcpy(buff, "2,");
// strcat(buff,buff_H);
// strcat(buff,",");
// strcat(buff,buff_L);
// strcat(buff,",");
// Serial.print(buff);
// if(XValue >= 0.0)
//     Serial.print(" ");
// Serial.print((float)XValue *SENSITIVITY,4);
// Serial.print(",");
// if(YValue >= 0.0)
//     Serial.print(" ");
// Serial.print((float)YValue *SENSITIVITY,4);
// Serial.print(",");
// if(ZValue >= 0.0)
//     Serial.print(" ");
// Serial.println((float)ZValue *SENSITIVITY,4);
