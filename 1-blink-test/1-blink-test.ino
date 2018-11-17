/*
  Blink
  Turns on an LED on for one second, then off for one second, repeatedly.
 
  This example code is in the public domain.
 */
 
// Pin 13 has an LED connected on most Arduino boards.
// give it a name:
int led = 13;
int i=0;

// the setup routine runs once when you press reset:
void setup() {                
  // initialize the digital pin as an output.
  pinMode(led, OUTPUT);
  Serial.begin(115200);
}

// the loop routine runs over and over again forever:
void loop() {
  digitalWrite(led, HIGH);   // turn the LED on (HIGH is the voltage level)
  delay(100);               // wait for a second
  digitalWrite(led, LOW);    // turn the LED off by making the voltage LOW
  delay(100);               // wait for a second
  //Serial.print(i);
  Serial.println("Hello world!");
  //I++;
}

// mega2560, default setting. 16MHz: 17373
// mega2560A, default setting. 10 MHz: 17373
// change MCU, F_CPU in Makefile, mega2560A : 17373
// + F_CPU specified in stk500boot.c, mega2560A: 17373
// + BAUDRATE specified in stk500boot.c, mega2560A: 
