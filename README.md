# Home Assistant Buderus EMS driver
This is a Buderus EMS bus driver for Home Assistant.

The interface is written in pure Python 3.

## Current status
Currently it only supports reading from the bus. Write support is about to come.

### Is it easy to use?
No. This is for hobby coders. To quickly integrate your Buderus unit into your favorite home automation, go to [BBQKees](https://bbqkees-electronics.nl/).

## Usage
1. Get a device with a 5V (TTL) or 3.3V serial port. The port must be able to send and receive BREAK signals. See the protocol description on Alexander Kabza's site referenced below to find out why.
    - The pl011 from the Raspberry Pi is such a port. It's [Mini UART will NOT work](https://www.raspberrypi.org/documentation/configuration/uart.md).
    - Any other SoC learning platform that runs Linux.
    - A USB TTL serial stick for your computer.
2. Get it connected to the heating unit. See links below.
3. Install your favorite Linux and Home Assistant on it.
4. Place the `buderus_ems` folder in `.homeassistant/custom_components`
5. Add this to the `configuration.yaml` (change the port if needed):

```
buderus_ems:
    device: /dev/ttyAMA0
```

## Supported systems
The interface is developed on my Raspberry Pi 3 running OpenSuSE tumbleweed aarch64.
I have no problems so far.

## Dependencies
Only Home Assistant v0.102.3 or later. It already brings the required packages (currently only Voluptuous).

## Thanks to
Please also check out these links if you want to learn more about the EMS protocol.

- [Alexander Kabza](http://www.kabza.de/MyHome/EMSbus.html), he wrote the readEMS.py, which I initially improved, but then did a rewrite (his python code does not parse the BREAK signal at the end of a telegramme).
- [Ingo Fischer](https://emswiki.thefischer.net/doku.php?id=start) for publishing detailed information about the bus protocol and the telegrammes on his Wiki.
- [Proddy](https://github.com/proddy/EMS-ESP) for his ESP8266 code, so far the most complete GPL3 implementation I could find and learn from.
- [BBQKees](https://bbqkees-electronics.nl/) for making and selling the EMS interface board. Considered the time and material, it was definitvely a better choice than soldering half a day.
