#!/usr/bin/python
# -*- coding: utf-8 -*-

#===============================================================================
#               TRK by Stan v 0.3.99
#===============================================================================

# Import bibliotek
from sterownik import *
import threading
import signal, os, sys, time
if sys.version_info[0] == 3:
  import importlib

try:
  import konf_polaczenie
except ImportError:
  raise ImportError('brak pliku konfiguracji polaczenia ze sterownikiem: konf_polaczenie.py')

c = sterownik(konf_polaczenie.ip, konf_polaczenie.login, konf_polaczenie.haslo);
c.getStatus()

try:
  import konf_TRK
except ImportError:
  raise ImportError('brak pliku konfiguracji parametrow pracy TRK: konf_TRK.py')

poprzednitryb = c.getTrybAuto()
if konf_TRK.autotrybmanual:
   c.setTrybAuto(False)

#===============================================================================
#                KOD PROGRAMU
#===============================================================================
blokNIC=0
blokSTART=1
blokNORMAL=2
blokSTOP=3
blokiHistoria = []
for y in range(12):
    blokiHistoria.append(blokNIC) 
blokiUruchomione=blokNIC
blokiPoprzednie=blokNIC
global tp
global td
tp = 0
td = 0
global czPod
global czPrz
global czNaw
global moNaw
global tZadGora
global tZadDol
global hist
global praca
global p
global d
global ts060
global razy_jeden
global byl_stop
byl_stop = False
global maxdelta
maxdelta = 0
global max_licznik
max_licznik = 0
global autodopalanie
autodopalanie = False
ts060 = 0
global opoznienie_licznik
opoznienie_licznik = 0
global kold
global knew
global nowakonfiguracja
nowakonfiguracja = False
global uruchomStop
uruchomStop = False
global ile_krokow
ile_krokow = len(konf_TRK.czas_podawania);
if not 't_min' in dir(konf_TRK):
  konf_TRK.t_min = [0] * ile_krokow
  print ('== Konfiguracja: brak sekcji t_min')
if not 't_max' in dir(konf_TRK):
  konf_TRK.t_max = [0] * ile_krokow
  print ('== Konfiguracja: brak sekcji t_max')
if not len(konf_TRK.t_min) == len(konf_TRK.t_max) == len(konf_TRK.czas_podawania) == len(konf_TRK.czas_przerwy) == len(konf_TRK.czas_nawiewu) == len(konf_TRK.moc_nawiewu) == len(konf_TRK.tryb):
   print ("Błąd: Zła ilość elementów w blokach")
   sys.exit()

razy_jeden = ile_krokow * [False];

#========= WATKI ==============================================================
from timer import *

def spaliny():
    global maxdelta
    global max_licznik
    global deltaspalin
    global autodopalanie
    global opoznienie_licznik
    global ts060
    wspaliny.stop()
    x = c.getTempSpaliny()
    daneTSpal.pop(0)
    daneTSpal.append(x)
    tts060 = ts060 
    ts020 = daneTSpal[-1] - daneTSpal[-3]
    ts060 = daneTSpal[-1] - daneTSpal[-1 -1 * 6 * 1]
    ts061 = daneTSpal[-2] - daneTSpal[-2 -1 * 6 * 1]
    ts120 = daneTSpal[-1] - daneTSpal[-1 -1 * 6 * 2]
    ts180 = daneTSpal[-1] - daneTSpal[-1 -1 * 6 * 3]
    tts060 = ts060 - tts060
    print ("trend TSpal: " + str(ts020) + "/20s "+ str(ts060) + "/60s "+ str(ts120) + "/120s "+ str(ts180) + "/180s")
    print ("trend tts060: " + str(tts060) + "/60s  tspalin:" + str(x) + " tco:"+ str(c.getTempCO()))
    
    if autodopalanie == True and wsd.is_running == False:
       c.setDmuchawa(True); #workaround - na wylaczajaca sie dmuchawe
       max_licznik = max_licznik + 1
       
       if (c.getTempCO() < konf_TRK.tempZadanaGora): 
          autodopalanie = False
          wspaliny.start()
          return
       
       if opoznienie_licznik != konf_TRK.opoznienie:
          opoznienie_licznik = opoznienie_licznik + 1
          wspaliny.start()
          return
       
       opoznienie_licznik = 0
       
       if ts060 < 0 and ts060 < maxdelta:
          maxdelta = abs(ts060)
       
       if max_licznik > 6 * 15:
          print ("*** MAX CZAS DOPALANIA OSIAGNIETO delta:"+str(maxdelta))
          deltaspalin = abs(maxdelta)*0.9
          autodopalanie = False
          wspaliny.start()
          return
       
       if c.getTempPodajnik() > konf_TRK.max_temp_podajnika:
          print ("*** MAX TEMP PODAJNIKA OSIAGNIETA")
          autodopalanie = False
          wspaliny.start()
          return

       #if x - 20 <= konf_TRK.tempZadanaDol:
       #   print("a")
       #   autodopalanie = False
       #   wspaliny.start()
       #   return

       if ts060 <= -konf_TRK.deltaspalin and x < konf_TRK.tspalin:
          print("b")
          autodopalanie = False
          wspaliny.start()
          return
      
       elif ts060 < -konf_TRK.deltaspalin and tts060 < 0:
          print("c")
          autodopalanie = False
          wspaliny.start()
          return

       elif ts060 > 0 and ts061 < 0:
          print("d")
          autodopalanie = False
          wspaliny.start()
          return
      
       delta = konf_TRK.tspalin - x
       if delta < 0:
          delta = delta / 2
       moc = c.getDmuchawaMoc()
       if ts060 == 0 or konf_TRK.staly_nadmuch:
          nowamoc = moc
       else:
          nowamoc = int(moc + delta/abs(ts060))
       
       if nowamoc > konf_TRK.max_obr_dmuchawy:
          nowamoc = konf_TRK.max_obr_dmuchawy

       if nowamoc < konf_TRK.min_obr_dmuchawy:
          nowamoc = konf_TRK.min_obr_dmuchawy
       
       print ("autodopalanie TSpal: " + str(x) + " delta: "+ str(delta) +" moc: "+ str(moc) + " nowamoc: "+ str(nowamoc))
       if moc != nowamoc:
          c.setDmuchawaMoc(nowamoc)
    else:
      max_licznik = 0
    wspaliny.start()

def status():
    wstatus.stop()
    c.getStatus()
    if c.getTrybAuto() == True:
       print ("*** UWAGA! sterownik w trybie AUTO")
    wstatus.start()

def files_to_timestamp(path):
    files = [os.path.join(path, f) for f in os.listdir(path)]
    return dict ([(f, os.path.getmtime(f)) for f in files])

def konfig():
    wkonf.stop()
    global kold
    global knew
    global nowakonfiguracja
    knew = files_to_timestamp(os.path.abspath(os.path.dirname(sys.argv[0])))
    added = [f for f in knew.keys() if not f in kold.keys()]
    removed = [f for f in kold.keys() if not f in knew.keys()]
    modified = []

    for f in kold.keys():
        if not f in removed:
           if os.path.getmtime(f) != kold.get(f):
              modified.append(f)
       
    kold = knew
    for f in modified:
        if os.path.isfile(f) and os.path.basename(f) == 'konf_TRK.py':
           nowakonfiguracja = True

    for f in added:
        if os.path.isfile(f) and os.path.basename(f) == 'konf_TRK.py':
           nowakonfiguracja = True
    
    wkonf.start()

def regulatorCWU():
    wcwu.stop()

    if (c.getTrybAuto() != True):
        print ("Regulator CWU...")
        if (c.getTempCO() > konf_TRK.tempZalaczeniaPomp):
            pompa = True
        if (c.getTempCO() < konf_TRK.tempZalaczeniaPomp - 5.0):
            pompa = False
        
        if c.getTempCO() < c.getTempCWU():
            pompa = False
          
        if (c.getTempCWU() > konf_TRK.T_dolna_CWU and not konf_TRK.CWU_jako_bufor):
            pompa = False
        #elif (c.getTempCO() < konf_TRK.tempZalaczeniaPomp - 5.0) or (c.getTempCWU() > konf_TRK.T_dolna_CWU) or (c.getTempCO() < c.getTempCWU()):
        if (pompa and c.getPompaCWU() == False):
            c.setPompaCWU(True);
            print ("*** CWU: ON")
        
        elif (not pompa and c.getPompaCWU() == True):
            c.setPompaCWU(False);
            print ("*** CWU: OFF")

    wcwu.start()

def regulatorCO():
    wco.stop()

    if (c.getTrybAuto() != True):
        print ("Regulator CO...")
        if (c.getTempCO() > konf_TRK.tempZalaczeniaPomp):
            pompa = True
        if (c.getTempCO() < konf_TRK.tempZalaczeniaPomp - 5.0):
            pompa = False
            
        a = ''
        if konf_TRK.Tryb_autolato and c.getTempZew() > konf_TRK.T_zewnetrzna_lato:
            pompa = False
            a = "AUTOLATO"
           
        if (pompa and c.getPompaCO() == False):
            c.setPompaCO(True)
            print ("*** CO->ON")
        elif (not pompa and c.getPompaCO() == True):
            c.setPompaCO(False)
            print ("*** CO->OFF " + a)
    
    wco.start()

def uruchomBloki():
    wbl.stop()
    pracaBloki()

def podtrzymanie():
    wpod.stop()
    print ("*** Podtrzymanie ...")
    #konf_TRK.czas_tla = 20
    #konf_TRK.tlo = 38
    pracaPieca(konf_TRK.podtrzymanie_podajnik,konf_TRK.podtrzymanie_przerwa + konf_TRK.podtrzymanie_podajnik,konf_TRK.podtrzymanie_przerwa,konf_TRK.podtrzymanie_nadmuch,False)
    #if tlo > 0:
    #    c.setDmuchawa(True);
    #    c.setDmuchawaMoc(konf_TRK.tlo);
    wpod.startInterval(konf_TRK.podtrzymanie_postoj*60)

def stopPodajnik():
    global p
    wsp.stop()
    c.setPodajnik(False);
    print ("== stop podajnik realny czas: "+ str(time.time() - tp))
    p = 0

def stopDmuchawa():
    global d
    global autodopalanie
    wsd.stop()
    while autodopalanie == True:
      time.sleep(0.01)
    
    c.setDmuchawa(False);
    print ("== stop dmuchawa realny czas: "+ str(time.time() - td))
    d = 0

c.getStatus()    
daneTSpal = []
x = c.getTempSpaliny()
# 60 * 10s.
for y in range(60):
    daneTSpal.append(x) 

wstatus = RTimer(status)
wstatus.startInterval(2)
wspaliny = RTimer(spaliny)
wspaliny.startInterval(10) # co 10s.
wcwu = RTimer(regulatorCWU)
wcwu.startInterval(10)
wco = RTimer(regulatorCO)
wco.startInterval(10)
kold = files_to_timestamp(os.path.abspath(os.path.dirname(sys.argv[0])))
wkonf = RTimer(konfig)
wkonf.startInterval(10)
wbl = RTimer(uruchomBloki)
wsp = RTimer(stopPodajnik)
wsd = RTimer(stopDmuchawa)
wpod = RTimer(podtrzymanie)

#========= FUNKCJA PRACA PIECA ==============================================================

def pracaPieca(czPod,czPrz,czNaw,moNaw,aspa):
    global autodopalanie
    global byl_stop
    global tp
    global td
    global p
    global d
    p = 0
    d = 0
    autodopalanie = False
    if czNaw >= czPrz:
        czNaw = czPrz
        
    if czNaw > 0:
        c.setDmuchawa(True);
        td = time.time()
        c.setDmuchawaMoc(moNaw);
        d = 1
        print ("== start dmuchawa na czas: " + str(czNaw) + "s moc:"+ str(moNaw) + "%")
        wsd.startInterval(czNaw)
        autodopalanie = aspa
        if autodopalanie == True:
           print ("=== Autodopalanie: ON")

    if czPod > 0:
        c.setPodajnik(True);
        tp = time.time()
        p = 1
        print ("== start podajnik na czas: " + str(czPod))
        wsp.startInterval(czPod)
        
    while p != 0 or d != 0:
        time.sleep(0.01)
    
    if aspa:
       byl_stop = True
    
    return

def nowyBlok(blok):
    global blokiUruchomione
    global blokiPoprzednie
    global blokiHistoria
    if blokiHistoria[-2] != blok or blokiHistoria[-1] != blok:
       blokiHistoria.pop(0)
       blokiHistoria.append(blok)
       blokiPoprzednie = blokiHistoria[-2]
       blokiUruchomione = blok
       
    print ("Historia blokow:"+str(blokiHistoria))

#=========== FUNKCJA SPRAWDZENIA TMPERATURY CO ===============================================

def tempCO(tZadGora,tZadDol):
    global blokiUruchomione
    global blokiPoprzednie
    global blokiHistoria
    global byl_stop
    global praca
    global hist
    global razy_jeden
    global uruchomStop
    ileSTART = 0
    ileSTOP = 0
    ileNORMAL = 0
    for t in konf_TRK.tryb:
        if t == 'start' or t =='1start':
          ileSTART += 1
        if t == 'stop' or t =='1stop':
          ileSTOP += 1
        if t == 'normal' or t =='1normal':
          ileNORMAL += 1

    tco = c.getTempCO()
    
    if ileSTOP > 0 and (tco >= tZadGora) and (tco < tZadGora + konf_TRK.histerezaBlokuStop or uruchomStop) \
            and ((blokiUruchomione == blokNORMAL or blokiUruchomione == blokSTART) and ileSTOP == 1 \
                 or (konf_TRK.wymuszonahistereza == True and ileSTOP > 1)):
        
        uruchomStop = False
        nowyBlok(blokSTOP)
        if blokiPoprzednie == blokNIC:
           byl_stop = False
        praca = 0
        hist = 0
        print ('*** uruchamiam bloki STOP')
        
    elif ileNORMAL > 0 and (tco >= tZadDol) and (tco < tZadGora or (ileSTOP == 0 and uruchomStop) ) \
            and (blokiUruchomione == blokSTART \
                 or (konf_TRK.wymuszonahistereza == True and ileNORMAL > 1)):
        
        nowyBlok(blokNORMAL)
        uruchomStop = False
        if ileSTOP > 0:
           uruchomStop = True
        if blokiPoprzednie == blokNIC:
           byl_stop = False
        praca = 1
        print ('*** uruchamiam bloki NORMAL')

    elif ileSTART > 0 and (tco < tZadDol):
        nowyBlok(blokSTART)
        uruchomStop = True
            
        if blokiPoprzednie == blokNIC:
           razy_jeden = ile_krokow * [False];
           byl_stop = False
        
        praca = 1
        hist = 1
        print ('*** uruchamiam bloki START')

    else:
        nowyBlok(blokNIC)
        uruchomStop = False
        praca = 0
        print ("*** Oczekiwanie...")
        time.sleep(5);
        
    print ("START <"+ str(tZadDol)+"<= NORMAL <"+ str(tZadGora)+"<= STOP <"+str(tZadGora + konf_TRK.histerezaBlokuStop)+"  tCO="+ str(tco) + "°C.")

    if blokiUruchomione == blokNIC:
        if wpod.is_running != True:
           wpod.startInterval(konf_TRK.podtrzymanie_postoj*60)
    else:
        if wpod.is_running == True:
           wpod.stop()

#================ Przertwarzanie bloków ===============================================

def pracaBloki():
    global razy_jeden
    global byl_stop
    while True:
        licznik = 0
        if (c.getTrybAuto() != True):
            tZadGora = konf_TRK.tempZadanaGora
            tZadDol = konf_TRK.tempZadanaDol
            tempCO(tZadGora,tZadDol)
            
            ostatni_blok = ile_krokow - 1
            
            if blokiUruchomione != blokNIC:
                for licznik in range(0,ile_krokow):
                    tMin = konf_TRK.t_min[licznik]
                    tMax = konf_TRK.t_max[licznik]
                    tCO = c.getTempCO()
                    if (tMin > 0) and (tCO<= tMin): continue;
                    if (tMax > 0) and (tMax < tCO): continue;
                    
                    if konf_TRK.czas_podawania[licznik] > 0:
                        czPod = konf_TRK.czas_podawania[licznik] + konf_TRK.czasPodawania
                    else:
                        czPod = 0
                    
                    if konf_TRK.czas_przerwy[licznik] > 0:
                        czPrz = konf_TRK.czas_przerwy[licznik] + konf_TRK.czas_podawania[licznik] + konf_TRK.czasPrzerwy + konf_TRK.czasPodawania
                    else:
                        czPrz = 0
                    
                    if konf_TRK.czas_nawiewu[licznik] > 0:
                        czNaw = konf_TRK.czas_nawiewu[licznik] + konf_TRK.czasNawiewu
                    else:
                        czNaw = 0
                    
                    if konf_TRK.moc_nawiewu[licznik] > 0:
                        moNaw = konf_TRK.moc_nawiewu[licznik] + konf_TRK.mocNawiewu
                    else:
                        moNaw = 0
                    
                    if konf_TRK.tryb_autodopalania and byl_stop == False:
                       asp = licznik == ostatni_blok
                    else:
                       asp = False

                    TRYB = konf_TRK.tryb[licznik]

                    if (blokiUruchomione == blokSTART):
                        if TRYB == 'start':
                            print ("uruchamiam blok START nr " + str(licznik))
                            pracaPieca(czPod,czPrz,czNaw,moNaw,asp)
                        elif TRYB == '1start' and razy_jeden[licznik] == False:
                            print ("uruchamiam blok 1START nr " + str(licznik))
                            razy_jeden[licznik] = True
                            pracaPieca(czPod,czPrz,czNaw,moNaw,asp)
                    elif (blokiUruchomione == blokNORMAL):
                        if TRYB == 'normal':
                            print ("uruchamiam blok NORMAL nr " + str(licznik))
                            pracaPieca(czPod,czPrz,czNaw,moNaw,asp)
                        elif TRYB == '1normal' and razy_jeden[licznik] == False:
                            print ("uruchamiam blok 1NORMAL nr " + str(licznik))
                            razy_jeden[licznik] = True
                            pracaPieca(czPod,czPrz,czNaw,moNaw,asp)
                    elif (blokiUruchomione == blokSTOP):
                        if TRYB == 'stop':
                            print ("uruchamiam blok STOP nr " + str(licznik))
                            pracaPieca(czPod,czPrz,czNaw,moNaw,asp)
                        elif TRYB == '1stop' and razy_jeden[licznik] == False:
                            print ("uruchamiam blok 1STOP nr " + str(licznik))
                            razy_jeden[licznik] = True
                            pracaPieca(czPod,czPrz,czNaw,moNaw,asp)
        else:
          time.sleep(0.5);

#=================================================================================================
#                  PROGRAM GŁÓWNY
#=================================================================================================
praca = 0
hist = 1
wbl.startInterval(1)

try:
    while True:
        if nowakonfiguracja == True:
           print ('== Konfiguracja: Wczytywanie ...')
           stare_tryby = konf_TRK.tryb
           if sys.version_info[0] == 3:
             importlib.reload(sys.modules["konf_TRK"])
           else:
             reload(sys.modules["konf_TRK"])
           nowakonfiguracja = False
           ile_krokow = len(konf_TRK.czas_podawania);
           if not 't_min' in dir(konf_TRK):
              konf_TRK.t_min = [0] * ile_krokow
              print ('== Konfiguracja: brak sekcji t_min')
           if not 't_max' in dir(konf_TRK):
              konf_TRK.t_max = [0] * ile_krokow
              print ('== Konfiguracja: brak sekcji t_max')
           if not len(konf_TRK.t_min) == len(konf_TRK.t_max) == len(konf_TRK.czas_podawania) == len(konf_TRK.czas_przerwy) == len(konf_TRK.czas_nawiewu) == len(konf_TRK.moc_nawiewu) == len(konf_TRK.tryb):
              print ("Błąd: Zła ilość elementów w blokach")
              if konf_TRK.autotrybmanual:
                c.setTrybAuto(poprzednitryb)
              os.kill(os.getpid(), signal.SIGTERM)
           
           if stare_tryby != konf_TRK.tryb:
              razy_jeden = ile_krokow * [False];
           
        time.sleep(0.2);

finally:
    print ("Kończę działanie ...")
    c.setDmuchawa(False);
    c.setPodajnik(False);
    c.setPompaCWU(False);
    c.setPompaCO(False);
    if konf_TRK.autotrybmanual:
       c.setTrybAuto(poprzednitryb)

    os.kill(os.getpid(), signal.SIGTERM)
