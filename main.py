from MRR import *
import sys

#sys.path.append('/home/cle333/nh')
#from helper import *

if __name__ == "__main__":
	########################################
	### Anleitung für Setup & Verwendung ###
	########################################

	while True:
		try:
			saveMarketSnapshot()
		except Exception as e:
			print(f"An error occurred: {e}")
		finally:
			print('Sleeping 300s...')
			time.sleep(300)
	exit()

	mrr = MiningRigRentals("sha256ab", decode=False, pretty=True, print_output=False) # MRR Objekt erstellen

	day = 1
	#day = (date.today() - date(2024, 6, 7)).days  # Setting a fixed date for debugging / testing.

	with open('20240607.json', 'r') as file:
		data = json.load(file) #load raw data for testing

	getProfitForRentingAllHashrate(mrr, data, 15, True)
	exportDailyProfits(mrr, data, True) #csv export


	exit()

	mrr = MiningRigRentals("sha256ab", decode=False, pretty=True, print_output=False) # MRR Objekt erstellen

	for rental in mrr.getRentals(historical = True):
	#print(rental.extend(0.5)) #Bei Bedarf verlängern
	    #print(rental)
	    print(rental.getGraphData())# graphData besteht jetzt aus timestamp und bereits bezahlten BTC


	#while True:
		#try:
			#saveMarketSnapshot()
		#except Exception as e:
			#print(f"An error occurred: {e}")
		#finally:
			#print('Sleeping 60s...')
			#time.sleep(60)


	# Pool Setup (einmalig mit diesen Funktionen einrichten)
	# Die Pool Profile ID die verwendet werden soll, sowie API Secret & Key sind in der settings.ini

	#profileID = mrr.createPoolProfile('Test Profil')
	#mrr.printPoolProfiles()
	#mrr.deletePoolProfile(profileID)
	#poolID = mrr.addPool(name, host, port, user, password)
	#mrr.printPools()
	#mrr.addPoolToProfile(profileID, poolID, priority=0)

	# Generell kannst du dich einfach an den ganzen Methoden in den Klassen orientieren.
	# In den __init__ sind einige Standard Variablen definiert, die du abrufen kannst


	################
	### EXAMPLES ###
	################

	#rigs = mrr.getRigs(lowestHashrateTH=0) # Gesamten Marktplatz abrufen (HR > 0)
	#for rig in rigs:
	    #print(rig.info())

		#	rental = rig.rent(3) # Rig mieten für 3h
		#	rental.extend(1) # rental um 1h verlängern


	# day = 1
	#day = (date.today() - date(2024, 6, 7)).days  # Setting a fixed date for debugging / testing.
	#getProfitForRentingAllHashrate(mrr, day, 15)
	#exportDailyProfits(mrr, day) #csv export
	#mrr.getCheapestRigFor3Hours().rent(3) #Bei Bedarf das günstigste Rig mit 3h minimum mieten


