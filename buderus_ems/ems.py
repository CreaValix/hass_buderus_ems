#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Buderus EMS bus driver by Alexander Simon
# The code is roughly based on
# - http://www.kabza.de/MyHome/EMSbus.html
# - https://emswiki.thefischer.net/doku.php?id=wiki:ems:telegramme
# - https://github.com/proddy/EMS-ESP/blob/master/src/ems.cpp

import time
import struct
import termios
import os
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
import threading

SERIAL_PORT = '/dev/ttyAMA0'
HTTP_PORT = 8014
printing = False

###############################################################
# CRC Check fuer EMS Telegramme
###############################################################
# Die Routine benoetigt als Parameter das gesamte Telegramm 
# inkl. <CRC> und das <Break>-signalisierende  "00" am Ende, 
# als String mit Hex-Zahlen ohne vorangeestellte '0x', jeweils 
# durch ein Leerzeichen voneinander getrennt. Der Rueckgabewert 
# ist True, wenn der CRC stimmt und False, falls nicht. 
# Fehlt das 00 als <Break>-Kennzeichnung, wird keine CRC-Pruefung 
# durchgefuehrt und auch kein Wert zurueckgegeben.
crc_lookup_table = [0x00, 0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x10, 0x12, 0x14, 0x16, 0x18, 0x1A, 0x1C, 0x1E,
                    0x20, 0x22, 0x24, 0x26, 0x28, 0x2A, 0x2C, 0x2E, 0x30, 0x32, 0x34, 0x36, 0x38, 0x3A, 0x3C, 0x3E,
                    0x40, 0x42, 0x44, 0x46, 0x48, 0x4A, 0x4C, 0x4E, 0x50, 0x52, 0x54, 0x56, 0x58, 0x5A, 0x5C, 0x5E,
                    0x60, 0x62, 0x64, 0x66, 0x68, 0x6A, 0x6C, 0x6E, 0x70, 0x72, 0x74, 0x76, 0x78, 0x7A, 0x7C, 0x7E,
                    0x80, 0x82, 0x84, 0x86, 0x88, 0x8A, 0x8C, 0x8E, 0x90, 0x92, 0x94, 0x96, 0x98, 0x9A, 0x9C, 0x9E,
                    0xA0, 0xA2, 0xA4, 0xA6, 0xA8, 0xAA, 0xAC, 0xAE, 0xB0, 0xB2, 0xB4, 0xB6, 0xB8, 0xBA, 0xBC, 0xBE,
                    0xC0, 0xC2, 0xC4, 0xC6, 0xC8, 0xCA, 0xCC, 0xCE, 0xD0, 0xD2, 0xD4, 0xD6, 0xD8, 0xDA, 0xDC, 0xDE,
                    0xE0, 0xE2, 0xE4, 0xE6, 0xE8, 0xEA, 0xEC, 0xEE, 0xF0, 0xF2, 0xF4, 0xF6, 0xF8, 0xFA, 0xFC, 0xFE,
                    0x19, 0x1B, 0x1D, 0x1F, 0x11, 0x13, 0x15, 0x17, 0x09, 0x0B, 0x0D, 0x0F, 0x01, 0x03, 0x05, 0x07,
                    0x39, 0x3B, 0x3D, 0x3F, 0x31, 0x33, 0x35, 0x37, 0x29, 0x2B, 0x2D, 0x2F, 0x21, 0x23, 0x25, 0x27,
                    0x59, 0x5B, 0x5D, 0x5F, 0x51, 0x53, 0x55, 0x57, 0x49, 0x4B, 0x4D, 0x4F, 0x41, 0x43, 0x45, 0x47,
                    0x79, 0x7B, 0x7D, 0x7F, 0x71, 0x73, 0x75, 0x77, 0x69, 0x6B, 0x6D, 0x6F, 0x61, 0x63, 0x65, 0x67,
                    0x99, 0x9B, 0x9D, 0x9F, 0x91, 0x93, 0x95, 0x97, 0x89, 0x8B, 0x8D, 0x8F, 0x81, 0x83, 0x85, 0x87,
                    0xB9, 0xBB, 0xBD, 0xBF, 0xB1, 0xB3, 0xB5, 0xB7, 0xA9, 0xAB, 0xAD, 0xAF, 0xA1, 0xA3, 0xA5, 0xA7,
                    0xD9, 0xDB, 0xDD, 0xDF, 0xD1, 0xD3, 0xD5, 0xD7, 0xC9, 0xCB, 0xCD, 0xCF, 0xC1, 0xC3, 0xC5, 0xC7,
                    0xF9, 0xFB, 0xFD, 0xFF, 0xF1, 0xF3, 0xF5, 0xF7, 0xE9, 0xEB, 0xED, 0xEF, 0xE1, 0xE3, 0xE5, 0xE7]
def crc_check(telegram):
    crc = 0
    for value in telegram[0:-1]:
        crc = crc_lookup_table[crc]
        crc ^= value
    return(crc == telegram[-1])

def open_serial(path):
    ser = os.open(path, os.O_RDWR | os.O_NOCTTY)
    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(ser)

    # Raw mode: Noncanonical mode, no input processing, no echo, no signals, no modem control.
    cflag &= ~termios.HUPCL
    cflag |= (termios.CLOCAL | termios.CREAD)
    lflag &= ~(termios.ICANON | termios.ECHO | termios.ECHOE |
                termios.ECHOK | termios.ECHONL |
                termios.ISIG | termios.IEXTEN)  # |termios.ECHOPRT
    for flag in ('ECHOCTL', 'ECHOKE'):  # netbsd workaround for Erk
        if hasattr(termios, flag):
            lflag &= ~getattr(termios, flag)
    oflag &= ~(termios.OPOST | termios.ONLCR | termios.OCRNL)
    iflag &= ~(termios.INLCR | termios.IGNCR | termios.ICRNL | termios.IGNBRK | termios.BRKINT)
    if hasattr(termios, 'IUCLC'):
        iflag &= ~termios.IUCLC
    # Enable parity marking. This is important as each telegramme is terminated by a BREAK signal.
    # Without it, we could not distinguish between two telegrammes.
    iflag |= termios.PARMRK

    # 9600 baud
    ispeed = ospeed = termios.B9600
    # 8 bits per character
    cflag &= ~(termios.CSIZE)
    cflag |= termios.CS8
    # No parity bit
    iflag &= ~(termios.INPCK | termios.ISTRIP)
    cflag &= ~(termios.PARENB | termios.PARODD | 0o10000000000)
    # One stop bit
    cflag &= ~(termios.CSTOPB)
    # No hardware or software flow control
    iflag &= ~(termios.IXON | termios.IXOFF)
    cflag &= ~(termios.CRTSCTS)
    # Buffer
    cc[termios.VMIN] = 1
    cc[termios.VTIME] = 0

    termios.tcsetattr(ser, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
    return(ser)

# https://domoticproject.com/wp-content/uploads/2018/03/EMSWiki-telegramme-DEU.pdf

status = {
    'uba_fast': {},
    'uba_slow': {},
    'uba_dw': {},
    'hk1': {},
    'rc_time': {},
    'uba_setvalues': {},
    'uba_runtime': {},
    'rc_outdoortemp': {},
}

# https://domoticproject.com/ems-bus-buderus-nefit-boiler/#0x18_8211UBA_Monitor_Fast
# https://emswiki.thefischer.net/doku.php?id=wiki:ems:telegramme#ubamonitorfast
def printUBAMonitorFast(values):
    parsed = {
        'timestamp': datetime.today().isoformat(),
        'flowTempSet': values[0],
        'flowTempIs': values[1] / 10,
        'burnPowSet': values[2],
        'burnPowIs': values[3],
        'gasValve1': bool(values[4] & 0x01),
        'gasValve2': bool(values[4] & 0x02),
        'fan': bool(values[4] & 0x04),
        'ignition': bool(values[4] & 0x08),
        'boilerPump': bool(values[4] & 0x20),
        'valveDrinkWater': bool(values[4] & 0x40),
        'drinkWaterCircPump': bool(values[4] & 0x80),
        'boilerTemp': None if values[5] == -32768 else values[5] / 10,
        'drinkWaterTemp': values[6] / 10,
        'flowReturnTemp': values[7] / 10,
        'flameCurrent': values[8] / 10,
        'systemPressure': values[9] / 10,
        'serviceCode': values[10].decode('ASCII'),
        'errorCode': values[11],
        'intakeTemp': values[12] / 10,
    }
    if printing:
        print('Vorlauf Solltemperatur         : {} °C'.format(parsed['flowTempSet'])) # Selected Flow Temperature
        print('Vorlauf Isttemperatur          : {} °C'.format(parsed['flowTempIs'])) # Current Flow Temperature
        print('Kessel maximale Leistung       : {} %'.format(parsed['burnPowSet'])) # Selected Burning Power
        print('Kessel aktuelle Leistung       : {} %'.format(parsed['burnPowIs'])) # Current Burning Power
        print('Magnetventil für 1. Stufe      : {}'.format('An' if parsed['gasValve1'] else 'Aus'))
        print('Magnetventil für 2. Stufe      : {}'.format('An' if parsed['gasValve2'] else 'Aus'))
        print('Gebläse                        : {}'.format('An' if parsed['fan'] else 'Aus'))
        print('Zündung                        : {}'.format('An' if parsed['ignition'] else 'Aus'))
        print('Kesselkreispumpe               : {}'.format('An' if parsed['boilerPump'] else 'Aus'))
        print('3-Wege-Ventil auf Warmwasser   : {}'.format('An' if parsed['valveDrinkWater'] else 'Aus'))
        print('Zirkulation                    : {}'.format('An' if parsed['drinkWaterCircPump'] else 'Aus'))
        print('Temperatur (DL-Erhitzer?)      : {} °C'.format(parsed['boilerTemp']))
        print('Wassertemperatur               : {} °C'.format(parsed['drinkWaterTemp']))
        print('Temperatur Rücklauf            : {} °C'.format(parsed['flowReturnTemp'])) #Current Flow Return Temperature
        print('Flammenstrom                   : {} µA'.format(parsed['flameCurrent'])) # Flame current
        print('Systemdruck                    : {} bar'.format(parsed['systemPressure'])) # System Pressure
        print('Service code                   : {}'.format(parsed['serviceCode']))
        print('Error code                     : {}'.format(parsed['errorCode']))
        print('Ansauglufttemperatur           : {}'.format(parsed['intakeTemp']))
    return(parsed)

def printUBAMonitorSlow(values):
    parsed = {
        'timestamp': datetime.today().isoformat(),
        'outsideTemp': values[0] / 10,
        'boilerTemp': None if values[1] == 0x8000 else values[1] / 10,
        'exhaustTemp': None if values[2] == -32768 else values[2] / 10,
        'pumpMod': values[3],
        'burnStarts': values[4] << 16 | values[5],
        'burnOperTot': values[6] << 16 | values[7],
        'burnOperStage2': values[8] << 16 | values[9],
        'burnOperHeat': values[10] << 16 | values[11],
        'burnOperDrinkWater': values[12] << 16 | values[13],
    }
    if printing:
        print('Außentemperatur                : {} °C'.format(parsed['outsideTemp']))
        print('Kessel-Ist-Temperatur          : {} °C'.format(parsed['boilerTemp']))
        print('Abgastemperatur                : {} °C'.format(parsed['exhaustTemp']))
        print('Pumpenmodulation               : {} %'.format(parsed['pumpMod']))
        print('Brennerstarts                  : {}'.format(parsed['burnStarts']))
        print('Betriebszeit komplett (Brenner): {} min'.format(parsed['burnOperTot']))
        print('Betriebszeit Brenner Stufe 2   : {} min'.format(parsed['burnOperStage2']))
        print('Betriebszeit heizen            : {} min'.format(parsed['burnOperHeat']))
        print('Noch eine Zeit                 : {} min'.format(parsed['burnOperDrinkWater']))
    return(parsed)

warmwassersysteme = [
    'Kein Warmwasser', 'Nach Durchlaufprinzip', 'Durchlaufprinzip mit kleinem Speicher', 'Speicherprinzip'
]
def printUBAMonitorWWMessage(values):
    parsed = {
        'timestamp': datetime.today().isoformat(),
        'tempSet': values[0],
        'sensor1tempIs': values[1] / 10,
        'sensor2TempIs': values[2] / 10,
        'dayMode': bool(values[3] & 0x01),
        'singleHeat': bool(values[3] & 0x02),
        'thermDesinfect': bool(values[3] & 0x04),
        'heatingEnabled': bool(values[3] & 0x08),
        'reHeat': bool(values[3] & 0x10),
        'setTempReached': bool(values[3] & 0x20),
        'sensor1Error': bool(values[4] & 0x01),
        'sensor2Error': bool(values[4] & 0x02),
        'generalError': bool(values[4] & 0x04),
        'desinfectError': bool(values[4] & 0x08),
        'circDayMode': bool(values[5] & 0x01),
        'circManual': bool(values[5] & 0x02),
        'circOn': bool(values[5] & 0x04),
        'heatingNow': bool(values[5] & 0x08),
        'systemType': values[6],
        'currentFlow': values[7] / 10,
        'heatingTime': values[8] << 16 | values[9],
        'heatingRuns': values[10] << 16 | values[11],
    }
    if printing:
        print('Warmwasser Temperatur Soll         : {} °C'.format(parsed['tempSet']))
        print('Warmwasser Temperatur Ist          : {} °C'.format(parsed['sensor1tempIs']))
        print('Warmwasser Temperatur Ist 2. Fühler: {} °C'.format(parsed['sensor2TempIs']))
        print('Tagbetrieb                         : {}'.format('Ja' if parsed['dayMode'] else 'Nein'))
        print('Einmalladung                       : {}'.format('An' if parsed['singleHeat'] else 'Aus'))
        print('Thermische Desinfektion            : {}'.format('An' if parsed['thermDesinfect'] else 'Aus'))
        print('Warmwasserbereitung                : {}'.format('An' if parsed['heatingEnabled'] else 'Aus'))
        print('Warmwassernachladung               : {}'.format('An' if parsed['reHeat'] else 'Aus'))
        print('Warmwasser-Temperatur OK           : {}'.format('Ja' if parsed['setTempReached'] else 'Nein'))
        print('Fühler 1 defekt                    : {}'.format('Ja' if parsed['sensor1Error'] else 'Nein'))
        print('Fühler 2 defekt                    : {}'.format('Ja' if parsed['sensor2Error'] else 'Nein'))
        print('Störung WW                         : {}'.format('Ja' if parsed['generalError'] else 'Nein'))
        print('Störung Desinfektion               : {}'.format('Ja' if parsed['desinfectError'] else 'Nein'))
        print('Zirkulation Tagbetrieb             : {}'.format('An' if parsed['circDayMode'] else 'Aus'))
        print('Zirkulation Manuell gestartet      : {}'.format('An' if parsed['circManual'] else 'Aus'))
        print('Zirkulation läuft                  : {}'.format('An' if parsed['circOn'] else 'Aus'))
        print('Ladevorgang WW läuft               : {}'.format('An' if parsed['heatingNow'] else 'Aus'))

        print('Art des Warmwassersystems          : {}'.format(warmwassersysteme[parsed['systemType']]))
        print('Wwarmwasser Durchfluss             : {} l/min'.format(parsed['currentFlow']))
        print('Warmwasserbereitungszeit           : {} min'.format(parsed['heatingTime']))
        print('Warmwasserbereitungen              : {}'.format(parsed['heatingRuns']))
    return(parsed)

def printHK1MonitorMessage(values):
    parsed = {
        'timestamp': datetime.today().isoformat(),
        'onOptimize': bool(values[0] & 0x01),
        'offOptimize': bool(values[0] & 0x02),
        'automatic': bool(values[0] & 0x04),
        'preferDrinkwater': bool(values[0] & 0x08),
        'screedDrying': bool(values[0] & 0x10),
        'vacationMode': bool(values[0] & 0x20),
        'frostProtection': bool(values[0] & 0x40),
        'manual': bool(values[0] & 0x80),
        'summerMode': bool(values[1] & 0x01),
        'dayMode': bool(values[1] & 0x02),
        'remoteDisconnected': bool(values[1] & 0x04),
        'remoteError': bool(values[1] & 0x08),
        'forwardFlowSensorError': bool(values[1] & 0x10),
        'maxForwardFlow': bool(values[1] & 0x20),
        'externalError': bool(values[1] & 0x40),
        'partyPauseMode': bool(values[1] & 0x80),
        'roomTempSet': values[2] / 2,
        'roomTempIs': None if values[3] == 32000 else values[3] / 10,
        'onOptimizeTime': values[4],
        'offOptimizeTime': values[5],
        'heatingCurve10Deg': values[6],
        'heatingCurve0Deg': values[7],
        'heatingCurveMinus10Deg': values[8],
        'roomTempAdaptionTime': values[9] / 100,
        'requestedBoilerPower': values[10],
        'state0': bool(values[11] & 0x01),
        'state1': bool(values[11] & 0x02),
        'stateParty': bool(values[11] & 0x04),
        'statePause': bool(values[11] & 0x08),
        'state4': bool(values[11] & 0x10),
        'state5': bool(values[11] & 0x20),
        'stateVacation': bool(values[11] & 0x40),
        'stateHoliday': bool(values[11] & 0x80),
        'calculatedForwardTemp': values[12],
    }
    if printing:
        print('Ausschaltoptimierung             : {}'.format('An' if values[0] & 0x01 else 'Aus'))
        print('Einschaltoptimierung             : {}'.format('An' if values[0] & 0x02 else 'Aus'))
        print('Automatikbetrieb                 : {}'.format('An' if values[0] & 0x04 else 'Aus'))
        print('WW-Vorrang                       : {}'.format('An' if values[0] & 0x08 else 'Aus'))
        print('Estrichtrocknung                 : {}'.format('An' if values[0] & 0x10 else 'Aus'))
        print('Urlaubsbetrieb                   : {}'.format('An' if values[0] & 0x20 else 'Aus'))
        print('Frostschutz                      : {}'.format('An' if values[0] & 0x40 else 'Aus'))
        print('Manuell                          : {}'.format('An' if values[0] & 0x80 else 'Aus'))

        print('Sommerbetrieb                    : {}'.format('An' if values[1] & 0x01 else 'Aus'))
        print('Tagbetrieb                       : {}'.format('An' if values[1] & 0x02 else 'Aus'))
        print('Keine Kommunikation mit FB (?)   : {}'.format('An' if values[1] & 0x04 else 'Aus'))
        print('FB fehlerhaft (?)                : {}'.format('An' if values[1] & 0x08 else 'Aus'))
        print('Fehler Vorlauffühler (?)         : {}'.format('An' if values[1] & 0x10 else 'Aus'))
        print('Maximaler Vorlauf                : {}'.format('An' if values[1] & 0x20 else 'Aus'))
        print('Externer Störeingang (?)         : {}'.format('An' if values[1] & 0x40 else 'Aus'))
        print('Party- Pausebetrieb              : {}'.format('An' if values[1] & 0x80 else 'Aus'))

        print('Raumtemperatur Soll              : {} °C'.format(values[2] / 2))
        print('Raumtemperatur Ist               : {} °C'.format('Abgeschaltet' if values[3] == 32000 else values[3] / 10))
        print('Einschaltoptimierungszeit        : {}'.format(values[4]))
        print('Ausschaltoptimierungszeit        : {}'.format(values[5]))
        print('Heizkreis1 Heizkurve 10°C        : {}'.format(values[6]))
        print('Heizkreis1 Heizkurve 0°C         : {}'.format(values[7]))
        print('Heizkreis1 Heizkurve -10°C       : {}'.format(values[8]))
        print('Raumtemperatur-Änderungsgeschwindigkeit         : {}'.format(values[9] / 100))
        print('Von diesem Heizkreis angeforderte Kesselleistung: {}'.format(values[10]))

        print('Schaltzustand ???                : {}'.format('An' if values[11] & 0x01 else 'Aus'))
        print('Schaltzustand ???                : {}'.format('An' if values[11] & 0x02 else 'Aus'))
        print('Schaltzustand Party              : {}'.format('An' if values[11] & 0x04 else 'Aus'))
        print('Schaltzustand Pause              : {}'.format('An' if values[11] & 0x08 else 'Aus'))
        print('Schaltzustand ???                : {}'.format('An' if values[11] & 0x10 else 'Aus'))
        print('Schaltzustand ???                : {}'.format('An' if values[11] & 0x20 else 'Aus'))
        print('Schaltzustand Urlaub             : {}'.format('An' if values[11] & 0x40 else 'Aus'))
        print('Schaltzustand Ferien             : {}'.format('An' if values[11] & 0x80 else 'Aus'))

        print('Berechnete Solltemperatur Vorlauf: {} °C'.format(values[12]))

        #print('Keine Raumtemperatur             : {}'.format('An' if values[13] & 0x02 else 'Aus'))
        #print('Keine Absenkung                  : {}'.format('An' if values[13] & 0x04 else 'Aus'))
        #print('Heizbetrieb an BC10 abgeschaltet : {}'.format('An' if values[13] & 0x08 else 'Aus'))
    return(parsed)

wochentage = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
def printRCTimeMessage(values):
    parsed = {
        'timestamp': datetime.today().isoformat(),
        'time': datetime(values[0] + 2000, values[1], values[3], values[2], values[4], values[5]).isoformat(),
        'dayOfWeek': bool(values[0] & 0x01),
        'summerTime': bool(values[0] & 0x02),
        'radioClock': bool(values[0] & 0x04),
        'timeBad': bool(values[0] & 0x08),
        'dateBad': bool(values[0] & 0x10),
        'clockRunning': bool(values[0] & 0x20),
    }
    if printing:
        print('Zeit              : {:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}'.format(values[0] + 2000, values[1], values[3], values[2], values[4], values[5]))
        print('Wochentag         : {}'.format(wochentage[values[6]]))
        print('Sommerzeit        : {}'.format('Ja' if values[7] & 0x01 else 'Nein'))
        print('Funkuhr           : {}'.format('Ja' if values[7] & 0x02 else 'Nein'))
        print('Uhrzeit fehlerhaft: {}'.format('Ja' if values[7] & 0x04 else 'Nein'))
        print('Datum fehlerhaft  : {}'.format('Ja' if values[7] & 0x08 else 'Nein'))
        print('Uhr läuft         : {}'.format('Ja' if values[7] & 0x10 else 'Nein'))
    return(parsed)

def printUBASollwerte(values):
    parsed = {
        'boilerTempSet': values[0],
        'requestedPowerHeating': values[1],
        'requestedPowerDrinkwater': values[2],
        'alwaysZero': values[3],
    }
    if printing:
        print('Kessel-Solltemperatur  : {} °C'.format(parsed['boilerTempSet']))
        print('Leistungsanforderung HK: {}'.format(parsed['requestedPowerHeating']))
        print('Leistungsanforderung WW: {}'.format(parsed['requestedPowerDrinkwater']))
        print('Immer 0                : {}'.format(parsed['alwaysZero']))
    return(parsed)

def printFlags(values):
    if printing:
        print('Wert 0: {}'.format(values[0]))
        print('Wert 1: {}'.format(values[1]))

def printUBABetriebszeit(values):
    parsed = {
        'timestamp': datetime.today().isoformat(),
        'totalRuntime': values[0] << 16 | values[1],
    }
    if printing:
        print('Gesamtbetriebszeit: {} min'.format(parsed['totalRuntime']))
    return(parsed)

def printRCOutdoorTempMessage(values):
    parsed = {
        'timestamp': datetime.today().isoformat(),
        'dampedOutdoorTemp': values[0],
    }
    if printing:
        print('Gedämpfte Außentemperatur: {} °C'.format(parsed['dampedOutdoorTemp']))
        print('Flags 1                  : {}'.format(values[1]))
        print('Flags 2                  : {}'.format(values[2]))
    return(parsed)

def printUBAParameterWW(values):
    if printing:
        print('Warmwassersystem vorhanden            : {}'.format('Ja' if values[0] & 0x08 else 'Nein'))
        print('Warmwasser am Kessel aktiviert        : {}'.format('Ja' if values[1] == 0xff else 'Nein'))
        print('Warmwasser Solltemperatur             : {} °C'.format(values[2]))
        print('Zirkulationspumpe vorhanden           : {}'.format('Ja' if values[3] == 0xff else 'Nein'))
        print('Schaltzyklus Zirkulationspumpe        : {} min'.format(values[4] * 3))
        print('Solltemperatur thermische Desinfektion: {} °C'.format(values[5]))
        print('Warmwassermodus am Kessel             : {}'.format('ECO' if values[6] == 0xdb else 'Comfort'))
        print('Art des Warmwassersystems             : {}'.format('3-W Ventil' if values[7] == 0xff else 'Ladepumpe'))

def printUBAErrorMessages(values):
    if printing:
        print('Displaycode                : {}'.format(values[0].decode('ASCII')))
        print('Fehlernummer               : {} (0x{:02x})'.format(values[1], values[1]))
        print('Zeitstempel                : {:04d}-{:02d}-{:02d} {:02d}:{:02d}'.format(
            (values[2] & 0x7f) + 2000, values[3], values[5], values[4], values[6]))
        print('Dauer                      : {} min'.format(values[7]))
        print('Busadresse der Fehlerquelle: 0x{:02x}'.format(values[8]))

def printUBADevices(values):
    parsed = {}
    if printing:
        print('Only present devices will be listed.')
    for byte_no in range(len(values)):
        byte = values[byte_no]
        for bit_no in range(8):
            num = '{:02d}'.format(byte_no * 8 + bit_no)
            present = bool(byte & (0x01 << bit_no))
            parsed['device' + num] = present
            if printing and present:
                print('Device {}: Present'.format(num))
    return(parsed)


messagedefinitions = [
    {'id': 0x06, 'name': 'RCTimeMessage', 'short': 'rc_time', 'len': 8, 'format': '>BBBBBBBB', 'print': printRCTimeMessage},
    {'id': 0x07, 'name': 'UBADevices', 'len': 12, 'format': '>BBBBBBBBBBBB', 'print': printUBADevices},
    {'id': 0x10, 'name': 'UBAErrorMessages1', 'len': 12, 'format': '>2sHBBBBBHB', 'print': printUBAErrorMessages},
    {'id': 0x11, 'name': 'UBAErrorMessages2', 'len': 12, 'format': '>2sHBBBBBHB', 'print': printUBAErrorMessages},
    {'id': 0x12, 'name': 'RCErrorMessages', 'len': 12, 'format': '>2sHBBBBBHB', 'print': printUBAErrorMessages},
    {'id': 0x14, 'name': 'UBABetriebszeit', 'len': 3, 'format': '>BH', 'print': printUBABetriebszeit},
    {'id': 0x18, 'name': 'UBAMonitorFast', 'short': 'uba_fast', 'len': 25, 'format': '>bhBBxxBxhhhHB2sHhx', 'print': printUBAMonitorFast},
    {'id': 0x19, 'name': 'UBAMonitorSlow', 'short': 'uba_slow', 'len': 25, 'format': '>hhhxxxBBHBHBHBHBH', 'print': printUBAMonitorSlow},
    {'id': 0x1a, 'name': 'UBASollwerte', 'short': 'uba_setvalues', 'len': 4, 'format': '>bBBB', 'print': printUBASollwerte},
    {'id': 0x1c, 'name': 'UBAWartungsmeldung', 'len': 28, 'format': '', 'print': None},
    {'id': 0xa2, 'name': 'Unknown 0x29', 'short': '', 'len': 1, 'format': '>B', 'print': None},
    {'id': 0x2a, 'name': 'Unknown 0x2A', 'len': 24, 'format': '', 'print': None},
    {'id': 0x33, 'name': 'UBAParameterWW', 'len': 11, 'format': '>BBbxxxBBbBB', 'print': printUBAParameterWW},
    {'id': 0x34, 'name': 'UBAMonitorWWMessage', 'short': 'uba_dw', 'len': 16, 'format': '>bhhBBBBBBHBH', 'print': printUBAMonitorWWMessage},
    {'id': 0x35, 'name': 'Flags', 'len': 2, 'format': '>BB', 'print': printFlags},
    {'id': 0x3e, 'name': 'Monitor Heating Circuit 1', 'short': 'hk1', 'len': 15, 'format': '>BBbhBBbbbHBBb', 'print': printHK1MonitorMessage},
    {'id': 0xa2, 'name': 'Unknown 0xA2', 'short': '', 'len': 10, 'format': '>BBBBBBBBBB', 'print': None},
    {'id': 0xa3, 'name': 'RCOutdoorTempMessage', 'len': 3, 'format': '>bBB', 'print': printRCOutdoorTempMessage},
    {'id': 0xa5, 'name': 'Unknown 0xA5', 'len': 28, 'format': '', 'print': None},
]

def is_set(x, n):
    return x & 2**n != 0

# https://emswiki.thefischer.net/doku.php?id=wiki:ems:ems-telegramme
devicenames = {
    0x00: 'unknown 0x00',
    0x01: 'unknown 0x01',
    0x04: 'RS232 Gateway',
    0x08: 'MC10',
    0x09: 'BC10',
    0x0A: 'Handterminal',
    0x0B: 'Computer',
    0x0C: 'Kaskade',
    0x0D: 'Modem',
    0x0E: 'Konverter',
    0x0F: 'Zeitmodul',
    0x10: 'RC30 / RC35',
    0x11: 'WM10',
    0x12: 'ZM EED',
    0x13: 'Gerät 1',
    0x14: 'Gerät 2',
    0x15: 'Gerät 3',
    0x16: 'Gerät 4',
    0x17: 'RC20 Heizkreis',
    0x18: 'RC20 Heizkreis 1',
    0x19: 'RC20 Heizkreis 2',
    0x1A: 'RC20 Heizkreis 3',
    0x1B: 'RC20 Heizkreis 4',
    0x1C: 'RC20 Heizkreis 5',
    0x1D: 'RC20 Heizkreis 6',
    0x1E: 'RC20 Heizkreis 7',
    0x1F: 'RC20 Heizkreis 8',
    0x20: 'Mischer Heizkreis 1',
    0x21: 'Mischer Heizkreis 2',
    0x22: 'Mischer Heizkreis 3',
    0x23: 'Mischer Heizkreis 4',
    0x24: 'Mischer Heizkreis 5',
    0x25: 'Mischer Heizkreis 6',
    0x26: 'Mischer Heizkreis 7',
    0x27: 'Mischer Heizkreis 8',
    0x28: 'Warmwasser Heizkreis 1',
    0x29: 'Warmwasser Heizkreis 2',
    0x2A: 'Warmwasser Heizkreis 3',
    0x2B: 'Warmwasser Heizkreis 4',
    0x2C: 'Warmwasser Heizkreis 5',
    0x2D: 'Warmwasser Heizkreis 6',
    0x2E: 'Warmwasser Heizkreis 7',
    0x2F: 'Warmwasser Heizkreis 8',
    0x30: 'Warmwasser Heizkreis 1',
    0x31: 'Warmwasser Heizkreis 2',
    0x32: 'Warmwasser Heizkreis 3',
    0x33: 'Warmwasser Heizkreis 4',
    0x34: 'Warmwasser Heizkreis 5',
    0x35: 'Warmwasser Heizkreis 6',
    0x36: 'Warmwasser Heizkreis 7',
    0x37: 'Warmwasser Heizkreis 8',
    0x38: 'Gerät 1',
    0x39: 'Gerät 2',
    0x3A: 'Gerät 3',
    0x3B: 'Gerät 4',
    0x3C: 'Gerät 5',
    0x3D: 'Gerät 6',
    0x3E: 'Gerät 7',
    0x3F: 'Gerät 8',
    0x40: 'Gerät 9',
    0x41: 'Gerät 10',
    0x42: 'Gerät 11',
    0x43: 'Gerät 12',
    0x44: 'Gerät 13',
    0x45: 'Gerät 14',
    0x46: 'Gerät 15',
    0x47: 'Gerät 16',
    0x48: 'Gerät 17',
    0x49: 'Gerät 18',
    0x4A: 'Gerät 19',
    0x4B: 'Gerät 20',
    0x4C: 'Gerät 21',
    0x4D: 'Gerät 22',
    0x4E: 'Gerät 23',
    0x4F: 'Gerät 24',
    0x50: 'Gerät 25',
    0x51: 'Gerät 26',
    0x52: 'Gerät 27',
    0x53: 'Gerät 28',
    0x54: 'Gerät 29',
    0x55: 'Gerät 30',
    0x56: 'Gerät 31',
    0x57: 'Gerät 32',
    0x58: 'Gerät 33',
    0x59: 'Gerät 34',
    0x5A: 'Gerät 35',
    0x5B: 'Gerät 36',
    0x5C: 'Gerät 37',
    0x5D: 'Gerät 38',
    0x5E: 'Gerät 39',
    0x5F: 'Gerät 40',
    0x60: 'Gerät 41',
    0x61: 'Gerät 42',
    0x62: 'Gerät 43',
    0x63: 'Gerät 44',
    0x64: 'Gerät 45',
    0x65: 'Gerät 46',
    0x66: 'Gerät 47',
    0x67: 'Gerät 48',
    0x68: 'Gerät 49',
    0x69: 'Gerät 50',
    0x6A: 'Gerät 51',
    0x6B: 'Gerät 52',
    0x6C: 'Gerät 53',
    0x6D: 'Gerät 54',
    0x6E: 'Gerät 55',
    0x6F: 'Gerät 56',
}

def parse_message(data, hass):
    # Polling requests and no data responses
    if len(data) == 1:
#        if data[0] & 0x80:
#            print('Master polling {} - {}'.format(data[0] & 0x7f, devicenames[data[0] & 0x7f]))
#        else:
#            print('No data from   {} - {}'.format(data[0], devicenames[data[0]]))
        return()

    if len(data) < 6:
        print('Message too short: {}'.format(data))
        return()

    # Print the message
#    print('       ', end='')
#    for i in range(len(data)):
#        print(' {:02d}'.format(i), end='')
#    print()

    # Read the header
    try:
        (src, dst, msgtype, offset) = struct.unpack('BBBB', data[0: 4])
    except Exception as e:
        print('Unpack failed: {}'.format(e))
        return()
    request = bool(dst & 0x80)
    if request:
        dst = dst & 0x7f
        print('Request  {} ({}) -> {} ({}) type 0x{:02x}, offset {}:'.format(
            devicenames[src], src, devicenames[dst], dst, msgtype, offset), end='')
    else:
        print('Response {} ({}) -> {} ({}) type 0x{:02x}, offset {}:'.format(
            devicenames[src], src, devicenames[dst], dst, msgtype, offset), end='')
    for i in range(4, len(data)):
        print(' {:02x}'.format(data[i]), end='')
    print()

    # Check CRC
    crc = crc_check(data)
    if not crc:
        print('Bad CRC')
        return()

    if not request:
        msgdef = next((m for m in messagedefinitions if m['id'] == msgtype), None)
        if msgdef:
            print(msgdef['name'])
            if len(data) - 5 != msgdef['len']:
                print('Wrong message length: {} <-> {}'.format(len(data) - 5, msgdef['len']))
            if msgdef['format']:
                try:
                    values = struct.unpack(msgdef['format'], data[4:-1])
                except Exception as e:
                    print('Unpack failed: {}'.format(e))
                    return()
                if msgdef['print']:
                    data = msgdef['print'](values)
                    if 'short' in msgdef:
                        status[msgdef['short']] = data
                        if hass:
                            hass.bus.fire('buderus_ems_received_' + msgdef['short'], data)
                else:
                    print('Missing print, values: {}'.format(values))
            else:
                print('Missing format')
        else:
            print('Missing definition')

# Start HTTP Server
class EMSHTTPHandler(BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
    def do_GET(s):
        if s.path == '' or s.path == '/':
            response = (200, 'text/plain', b'foobar')
        elif s.path == '/status':
            try:
                response = (200, 'application/json', json.dumps(status, indent=4).encode('UTF-8'))
            except Exception as e:
                response = (500, 'text/plain', ('Cannot create JSON: {}'.format(e)).encode('UTF-8'))
        else:
            response = (404, 'text/plain', b'Path not found')
        s.send_response(response[0])
        s.send_header('Content-type', response[1])
        s.end_headers()
        s.wfile.write(response[2])
def start_server():
    print('Starting HTTP server on port {}'.format(HTTP_PORT))
    httpd = HTTPServer(('localhost', HTTP_PORT), EMSHTTPHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    print('Ending HTTP server on port {}'.format(HTTP_PORT))
    httpd.server_close()

def start_http_server():
    daemon = threading.Thread(name='daemon_server', target=start_server)
    daemon.setDaemon(True) # Set as a daemon so it will be killed once the main thread is dead.
    daemon.start()

def mainloop(port, hass):
    telegram = b''
    parity_errors = False
    parity = 0
    while 1:
        char = os.read(port, 1)
        if len(char) != 1:
            continue
        if parity == 0 and char == b'\xff':
            # We got a parity mark charater.
            parity = 1
            continue
        elif parity == 1:
            # Character after parity mark
            if char == b'\x00':
                # Parity error or break signal
                parity = 2
            elif char == b'\xff':
                telegram += b'\xff'
                parity = 0
            else:
                print('Wrong character after parity mark ignored.')
                parity = 0
            continue
        elif parity == 2:
            # 2nd character after parity mark
            if char == b'\x00':
                # Break signal. The message is complete.
                parse_message(telegram, hass)
                telegram = b''
                parity_errors = False
                parity = 0
                continue
            else:
                # Save the error but yet add the character.
                parity_errors = True
        telegram += char

if __name__ == '__main__':
    #global printing
    #printing = True
    start_http_server()
    port = open_serial(SERIAL_PORT)
    mainloop(port, None)
