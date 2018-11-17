
def PSD_Plot():
    global dataPSD, nAverageOfPSD, NFFT, Pxx, Fs

    nAverageOfPSD += 1
    dpi = 80
    figure(1, figsize=(320/dpi, 240/dpi))
    clf()
    for i in range(3):
        f, Pxx_ = signal.welch(signal.detrend(data4PSD[:, i]), int(Fs), nperseg=NFFT)
        Pxx[:, i] = (nAverageOfPSD - 1) / nAverageOfPSD * Pxx[:, i] + Pxx_ / (nAverageOfPSD)
        semilogy(f, Pxx[:, i])
    xlabel('Frequency (Hz)')
    ylabel('PSD (g^2/Hz)')
    Fn = Fs/2
    gca().set_xlim([0, Fn])
    gca().yaxis.set_label_coords(-0.10, 0.5)
    subplots_adjust(left=0.13, bottom=0.15, right=0.95, top=0.95)
    savefig('.psd.png', dpi=80)
    close(1)

    pygame.display.init()
    pygame.mouse.set_visible(False)
    lcd = pygame.display.set_mode((320, 240))
    feed_surface = pygame.image.load('.psd.png')
    lcd.blit(feed_surface, (0, 0))
    pygame.display.update()
    sleep(0.05)
    return
    
def timehistoryPlot():
    global data4THP, Fs, dt

    dpi = 80
    figure(1, figsize=(320/dpi, 240/dpi))
    clf()
    plot(time4THP, data4THP)
    ylabel('ACC (g)')
    xlabel('Time (MM:SS)')
    gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    gca().set_xlim([time4THP[0], time4THP[-1] + datetime.timedelta(seconds=dt)])
    gca().yaxis.set_label_coords(-0.10, 0.5)
    subplots_adjust(left=0.13, bottom=0.15, right=0.95, top=0.95)
    savefig('.thp.png', dpi=80)
    close(1)

    pygame.display.init()
    pygame.mouse.set_visible(False)
    lcd = pygame.display.set_mode((320, 240))
    feed_surface = pygame.image.load('.thp.png')
    lcd.blit(feed_surface, (0, 0))
    pygame.display.update()
    sleep(0.05)
    return


# PYGAME
os.putenv('SDL_FBDEV', '/dev/fb1')
pygame.init()

# BUTTON SETTING
Buttons = [{'Number': 17,
            'readingPrev': 1,
            'timeDetected': now,
            'isPressed': False,
            'cmd': 'd',
            'dstate': -1},
           {'Number': 22,
            'readingPrev': 1,
            'timeDetected': now,
            'isPressed': False,
            'cmd': 'u',
            'dstate': 1}]
debounce = datetime.timedelta(0, 0, 0, 200)
GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
