/*
 * DS18B20 TEMPERATURE SENSOR SOFTWARE 
 *
 * USE THE 1-WIRE SENSORS TO ACQUIRE TEMPERATURE DATA 
 *
 * OUTPUT: 
 * 	Measurement files at ~/data/ 
 *
 * BY Ki Young Koo
 *
 * Revision:
 *    3rd Jan 2017: option for SAMPLING_PERIOD added
 * 
 */

#include <stdio.h>
#include <dirent.h>
#include <string.h>
#include <stdbool.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include <wiringPi.h>
#include <time.h>
#include <errno.h>
#include <sys/stat.h>

#define DEBUG false
#define SAMPLING_PERIOD 60 // in seconds

char timestring[50];
int state = 1;
DIR *dir;
struct dirent *dirent;
char buf[256];     // Data from device
char tmpData[6];   // Temp C * 1000 reported by device 
const char path[] = "/sys/bus/w1/devices"; 
ssize_t numRead;
int i = 0;
int devCnt = 0;
  char dev[10][16];
  char devPath[10][128];

typedef struct
{
  int ButtonNumber;
  int ReadingNow;
  int ReadingPrev;
  unsigned int timeDetected;
  bool isPressed;
} button;

button buttons[3];

unsigned int time_last = 0;         // the last time the output pin was toggled
unsigned int debounce = 200;   // the debounce time, increase if the output flickers

time_t currentTime = 0;
time_t samplingTime = 0;

void readSystemTime(){
  time_t t = time(NULL);
  struct timespec gettime_now;
  clock_gettime(CLOCK_REALTIME, &gettime_now);
  t = gettime_now.tv_sec;
  struct tm tm = *localtime(&t);

  sprintf(timestring,"%d-%.2d-%.2d %.2d:%.2d:%.2d.%.9ld", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec, gettime_now.tv_nsec);
  return;
}

void logMeasurement(char* devName, float temperature){

  FILE* fd;
  char path2Logfile[50];


  /* CHECK IF DATA FOLDER EXISTS */

  DIR* dir = opendir("/home/pi/data");
  if(dir){
    closedir(dir);
  }else if(ENOENT == errno){
    mkdir("/home/pi/data",0700);
  }

  strcpy(path2Logfile,"/home/pi/data/");
  strcat(path2Logfile,devName);
  strcat(path2Logfile,".txt");
  //printf("%s\n",path2Logfile);

  fd = fopen(path2Logfile,"a");
  fprintf(fd,"%s, %f\n",timestring,temperature/1000);
  fclose(fd);
}

void single_measure(){
  int i;
  char timestring_s[10];

  readSystemTime();
  memcpy(timestring_s,&timestring[11],8);
  timestring_s[8]='\0';
  printf(" %s",timestring_s);

  if(DEBUG)
    printf("Before the for-loop\n");

  for(i=0; i<devCnt; i++){
    int fd = open(devPath[i], O_RDONLY);
    if(fd == -1){
  perror ("Couldn't open the w1 device.");
  return;
    }
    if(DEBUG)
  printf("After open\n");

    while((numRead = read(fd, buf, 256)) > 0){
  strncpy(tmpData, strstr(buf, "t=") + 2, 6);
  if(DEBUG)
	printf("After strncpy\n");
  float tempC = strtof(tmpData, NULL);
  if( i<devCnt-1){
	printf(" %.3f",tempC/1000);
  }else{
	printf(" %.3f\n",tempC/1000);
  }
  if(DEBUG)
	printf("Before logMeasurement\n");
  logMeasurement(dev[i],tempC);
    }
    close(fd);
  }
  return;
}

bool time2Measure(){
    struct timespec gettime_now;
    clock_gettime(CLOCK_REALTIME, &gettime_now);
    currentTime = gettime_now.tv_sec;

    if(samplingTime == 0){
  // SET SAMPLINGTIME IF NOT SET
  samplingTime = (currentTime/SAMPLING_PERIOD+1)*SAMPLING_PERIOD;
  return false;
    }else if(currentTime < samplingTime){
  // NOT THE SAMPLINGTIME YET
  return false;
    }else{
  // NOW IS THE TIME
  samplingTime += SAMPLING_PERIOD;
  return true;
    }
}

int main (void) {

// 1ST PASS COUNTS DEVICES
dir = opendir (path);
if (dir != NULL)
  {
    while ((dirent = readdir (dir))) {
  // 1-wire devices are links beginning with 28-
  if (dirent->d_type == DT_LNK &&
	  strstr(dirent->d_name, "28-") != NULL) {
	i++;
  }
    }
    (void) closedir (dir);
  }
 else
   {
     perror ("Couldn't open the w1 devices directory");
     return 1;
   }
devCnt = i;
i = 0;

// 2ND PASS ALLOCATES SPACE FOR DATA BASED ON DEVICE COUNT
dir = opendir (path);
if (dir != NULL)
  {
    while ((dirent = readdir (dir))) {
  // 1-wire devices are links beginning with 28-
  if (dirent->d_type == DT_LNK && 
	  strstr(dirent->d_name, "28-") != NULL) { 
	strcpy(dev[i], dirent->d_name);
	// Assemble path to OneWire device
	sprintf(devPath[i], "%s/%s/w1_slave", path, dev[i]);
	i++;
  }
    }
    (void) closedir (dir);
  }
 else
   {
     perror ("Couldn't open the w1 devices directory");
     return 1;
   }
i = 0;

printf("-----------------------------\n");
printf(" Welcome to Temperature Node \n");
printf("-----------------------------\n");
printf("State=1: ready to measure...\n");

// WiringPi
wiringPiSetupGpio();

// Button setup
buttons[0].ButtonNumber = 27;
buttons[1].ButtonNumber = 22;
buttons[2].ButtonNumber = 17;
for(i=0; i<3; i++){
  pinMode(buttons[i].ButtonNumber,INPUT);
  pullUpDnControl(buttons[i].ButtonNumber,PUD_UP);
 }
for(i=0; i<3; i++){
  buttons[i].ReadingNow = HIGH;
  buttons[i].ReadingPrev = HIGH;
  buttons[i].timeDetected = 0L;
  buttons[i].isPressed = false;
 }

// Read temp continuously
// Opening the device's file triggers new reading
while(1) {

  if(DEBUG) printf("in the loop\n");

  /* DETECTING BUTTON PRESSINGS */

  int ibutton, Reading, ReadingPrev;
  for(ibutton = 0; ibutton < 3; ibutton++){
    Reading     = digitalRead(buttons[ibutton].ButtonNumber);
    ReadingPrev = buttons[ibutton].ReadingPrev;
    time_last        = buttons[ibutton].timeDetected;
    if(Reading == LOW && ReadingPrev == HIGH && millis() - time_last > debounce){
		buttons[ibutton].isPressed = true;
		buttons[ibutton].timeDetected = millis();	
    }
    buttons[ibutton].ReadingPrev = Reading;
  }

  /* CALLBACK FUNCTIONS FOR A SWITCH PRESSING */
  /* state 1: Ready   */
  /* state 2: DAQ	state  */


  /* UP button */
  if(buttons[1].isPressed == true){
    buttons[1].isPressed = false;
    if(state == 1){
		state = 2;
		printf("State=2: measuring... \n");
		printf(" TIME    ");
		for(i=0;i<devCnt;i++){
		  printf(" %s  ",(dev[i]+11));
		}
		printf("\n");

    }
  }

  /* DOWN button */
  if(buttons[2].isPressed == true){
    buttons[2].isPressed = false;
    if(state==2){
		state = 1;
		printf("State=1: ready to measure...\n");
    }
  }

  /* STATE DEPENDENT ROUTINES */

    if(DEBUG) printf("State=%d\n",state);

    if(state==1)
		delay(100);

    if(state==2){
		// Measure!
		if(time2Measure()==false){
			continue;
		}else{
			single_measure();
		}

    }
}

return 0;
}
