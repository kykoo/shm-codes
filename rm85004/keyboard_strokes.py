
def isKeyStrokeAvailable():
    import select
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

# STORE TERMINAL SETTING
old_settings = termios.tcgetattr(sys.stdin)

termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
