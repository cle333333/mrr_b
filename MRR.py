import time, hashlib, hmac, json, os, requests, configparser, zipfile, shutil, csv
from datetime import datetime, timedelta, date
import numpy as np

algos = ['sha256', 'sha256ab']
### Main functions ###
def getProfitForRentingAllHashrate(mrr, daysPast, beginningAtProfit):
    day = FullDay(mrr,mrr.getDate(daysPast))

    beginningAtProfitFactor = (beginningAtProfit/100)+1 # z.B. 10% -> 1.1

    priceTotal = 0
    profitTotal = 0

    for i in range(len(day.timestamps) - 1):
        timestamp = day.timestamps[i]
        snapshot = Snapshot(day, timestamp)

        for rigData in snapshot.data:
            rig = Rig(day.mrr, rigData)
            rigProfitFactor = rig.getProfitFactor(snapshot.breakEvenPoint)

            if rigProfitFactor >= beginningAtProfitFactor:
                rigPeriodPrice = snapshot.periodDurationDays * rig.price * rig.hashrate_advertised_eh
                rigPeriodRevenue = rigPeriodPrice * rigProfitFactor
                periodProfit = rigPeriodRevenue - rigPeriodPrice

                priceTotal += rigPeriodPrice
                profitTotal += periodProfit

    print(priceTotal, profitTotal)
def exportDailyProfits(mrr, pastDays):
    day = FullDay(mrr,mrr.getDate(pastDays))

    exportData = {}
    hashrateRanges = [-50, -40, -30, -20, -10, -5, -3, -2, -1, 0, 0.5, 1, 1.5, 2, 3, 5, 10, 20, 30, 40, 50, float('inf')]

    for timestamp, allRigsAtTimestamp in day.data.items():
        snapshot = Snapshot(day, timestamp)

        totalHashrateAtTimestamp = 0
        hashrateDistribution = hashrateDistributionPercentage = [0.0] * len(hashrateRanges)

        for rigData in allRigsAtTimestamp:
            rig = Rig(day.mrr, rigData)
            totalHashrateAtTimestamp += rig.hashrate_advertised_eh

            for i, upperLimit in enumerate(hashrateRanges):
                if rig.getProfitability(snapshot.breakEvenPoint) < upperLimit:
                    hashrateDistribution[i] = hashrateDistribution[i] + rig.hashrate_advertised_eh
                    break
        for i in range(len(hashrateDistribution)):
            hashrateDistributionPercentage[i] = hashrateDistribution[i] / totalHashrateAtTimestamp

        exportData[timestamp] = {
            'hr': totalHashrateAtTimestamp,
            'hrDistribution': hashrateDistributionPercentage
        }

    finalList = []
    for timestamp, data in exportData.items():
        data['hr'] = str(data['hr'])
        data['hrDistribution'] = [str(v) for v in data['hrDistribution']]
        finalList.append([timestamp]+[data['hr']]+data['hrDistribution'])
    saveListToCSV(finalList, mrr.path_export+day.date+'.csv')


    limitsData = []
    limitsData.append(hashrateRanges)

    timestampDayStart = int(datetime.strptime(day.date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    breakEvenPoint = day.getBreakEvenPoint(timestampDayStart)

    priceLimits = [0.0] * len(hashrateRanges)

    for i, percent in enumerate(hashrateRanges):
        priceTest = breakEvenPoint / (1 + (percent / 100))
        priceLimits[i] = str(priceTest)
    limitsData.append(priceLimits)


    saveListToCSV(limitsData, mrr.path_export + day.date + '_limits.csv')
def saveMarketSnapshot():
	for algo in algos:
		mrr = MiningRigRentals(algo, decode=False, pretty=True, print_output=False)
		filePath = mrr.path_data_raw + str(int(time.time())) + ".json"
		saveToFile(json.dumps(mrr.getRigsData()), filePath)
		print('Snapshot saved: ' + filePath)  # z.B. 2024_04_28-14_17_20.txt
def zipDay(numberDaysBehind=1):
	config = configparser.ConfigParser()
	config.read('/home/cle333/mrr/settings.ini')

	for algo in algos:
		path_data_raw = config['MRR']['path_data_raw'] + algo + '/'
		path_data_compressed = config['MRR']['path_data_compressed'] + algo + '/'
		path_temp = config['MRR']['path_temp']
		if not os.path.exists(path_temp): os.makedirs(path_temp)

		date_behind = datetime.now() - timedelta(days=numberDaysBehind)
		date_behind_str = date_behind.strftime('%Y-%m-%d')
		start_of_date = int(date_behind.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
		end_of_date = int(date_behind.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp())

		full_day_filename = f"{date_behind_str}.json"
		tempFile = full_day_filename

		zip_filename = f"{date_behind_str}.zip"
		zip_file_path = path_data_compressed + zip_filename

		data = {}

		if not os.path.exists(zip_file_path):
			# collect all data
			for filename in os.listdir(path_data_raw):
				if filename.endswith(".json") and filename[:-5].isdigit():
					timestamp = int(filename[:-5])

					if start_of_date <= timestamp <= end_of_date:
						with open(os.path.join(path_data_raw, filename), 'r') as file:
							data[str(timestamp)] = json.load(file)

			# create ZIP from data
			if len(data) > 0:
				with open(tempFile, 'w') as file: # Write data to json file
					json.dump(data, file, indent=4)

				with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zfile:
					zfile.write(tempFile, arcname=full_day_filename)

				os.remove(tempFile)
			else:
				print(algo + " - No files found for yesterday")


### Hashrate calculation ###
def getHashRateFromDifficulty(difficulty):
	hashrate = difficulty / float(600) * pow(2, 32)
	hashrateEH = hashrate / 1000 / 1000 / 1000 / 1000 / 1000 / 1000
	return hashrateEH
### File handling ###
def saveListToCSV(listData, csvFileName):
	if os.path.exists(csvFileName):
		if input(f"Die Datei {csvFileName} existiert bereits. Möchten Sie sie löschen? (y/n): ").lower() == 'y':
			os.remove(csvFileName)
		else:
			print("Datei wurde nicht gelöscht. Vorgang abgebrochen.")
			exit()

	with open(csvFileName, 'w', newline='') as csvFile:
		writer = csv.writer(csvFile, delimiter=',')
		for values in listData:
			writer.writerow(values)
def saveToFile(data, file_path):
    with open(file_path, "w") as file:
        file.write(data)

class MiningRigRentals:
	def __init__(self, algo, decode=True, pretty=False, print_output=False):
		self.config = configparser.ConfigParser()
		#self.config.read('settings.ini')
		self.config.read('/home/cle333/mrr/settings.ini') #!!!

		self.key = self.config['MRR']['key']
		self.secret = self.config['MRR']['secret']
		self.path_data_raw = self.config['MRR']['path_data_raw'] + algo + '/'
		self.path_data_compressed = self.config['MRR']['path_data_compressed'] + algo + '/'
		self.path_temp = self.config['MRR']['path_temp']
		self.path_export = self.config['MRR']['path_export']
		self.path_blockchain_data = self.config['MRR']['path_blockchain_data']
		self.poolProfileID = self.config['MRR']['pool_profile_id']

		self.block_reward = float(self.config['Blockchain']['block_reward'])

		if not os.path.exists(self.path_data_raw): os.makedirs(self.path_data_raw)
		if not os.path.exists(self.path_data_compressed): os.makedirs(self.path_data_compressed)
		if not os.path.exists(self.path_export): os.makedirs(self.path_export)

		self.decode = decode
		self.pretty = pretty
		self.print_output = print_output

		self.algo = algo

		self.allRigs = {}
		self.allRentals = {}

		self.allBlocks = self.getAllBlocks()

#Main API query
	root_uri = "https://www.miningrigrentals.com/api/v2"
	def query(self, request_type, endpoint, parms=None):
		if parms is None:
			parms = {}

		rest = ""
		# if there are any URL params, remove it for the signature
		if "?" in endpoint:
			endpoint, rest = endpoint.split("?", 1)
			rest = "?" + rest

		# URI is our root_uri + the endpoint
		uri = self.root_uri + endpoint + rest

		headers = {
			'Content-Type': 'application/json',
		}

		if self.pretty:
			if "?" not in uri:
				uri += '?pretty'
			else:
				uri += "&pretty"

		# Get an incrementing/unique nonce
		nonce = str(int(time.time() * 1000))

		# String to sign is api_key + nonce + endpoint
		sign_string = self.key + nonce + endpoint

		# Sign the string using a sha1 hmac
		sign = hmac.new(self.secret.encode(), sign_string.encode(), hashlib.sha1).hexdigest()

		# Headers to include our key, signature, and nonce
		headers.update({
			'x-api-key': self.key,
			'x-api-sign': sign,
			'x-api-nonce': nonce,
		})

		# Requests setup
		if request_type in ['DELETE']:
			response = requests.request(request_type, uri, headers=headers)
		else:
			response = requests.request(request_type, uri, headers=headers, data=json.dumps(parms))

		# Print request if print_output is enabled
		if self.print_output:
			print(f"{request_type} {uri}")

		return {
			'status': response.status_code,
			'header': response.headers,
			'data': response.text
		}
	def parse_return(self, array):
		data = array if array["status"] != 200 else json.loads(array["data"]) if self.decode else array["data"]

		if self.print_output:
			print("\nReturned Data::\n")
			print(json.dumps(data, indent=4) if isinstance(data, dict) else data)
			print("\n")
		else:
			return data
	def get(self, endpoint, parms=None):
		return self.parse_return(self.query("GET", endpoint, parms))
	def post(self, endpoint, parms=None):
		return self.parse_return(self.query("POST", endpoint, parms))
	def put(self, endpoint, parms=None):
		return self.parse_return(self.query("PUT", endpoint, parms))
	def delete(self, endpoint, parms=None):
		return self.parse_return(self.query("DELETE", endpoint, parms))

#General
	def getDate(self,pastDays=0):
		return (datetime.now() - timedelta(days=pastDays)).strftime('%Y-%m-%d')

#Blockchain
	def getAllBlocks(self):
		allBlocks = []
		with open(self.path_blockchain_data, mode='r') as file:
			reader = csv.reader(file)
			for row in reader:
				row[0] = int(float(row[0]))  # Blockheight
				row[1] = int(float(row[1]))  # UNIX Time
				row[2] = int(float(row[2]))  # Fees in sat
				row[3] = float(row[3])  # Difficulty
				allBlocks.append(row)
		return allBlocks
	def getBlocks(self, date):
		day = datetime.strptime(date, "%Y-%m-%d")
		day_blocks = []
		for block in self.allBlocks:
			blockheight, unixTimestamp, fees, diff = block

			timestampStart = int(day.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
			timestampEnd = int(day.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp())

			if timestampStart <= unixTimestamp <= timestampEnd:
				day_blocks.append(block)
		return day_blocks
	def getLastBlockFromTimestamp(self,timestamp):
		lastBlock = 0
		for block in self.allBlocks:
			blockheight, unixTimestamp, fees, diff = block

			if unixTimestamp >= int(timestamp):
				return lastBlock
			lastBlock = block
#/info/algos
	def getAlgos(self):
		result = json.loads(self.get('/info/algos'))
		if not result['success']: return False
		return result['data']

#/account/balance
	def getBtcBalance(self):
		result = json.loads(self.get('/account/balance'))
		if not result['success']: return False
		return float(result['data']['BTC']['confirmed'])
	def getBtcBalanceUnconfirmed(self):
		result = json.loads(self.get('/account/balance'))
		if not result['success']: return False
		return float(result['data']['BTC']['unconfirmed'])

#/rental
	def getRentals(self, historical=False):
		finished = False
		offset = 0
		rentals = []
		while not finished:
			result = json.loads(self.get("/rental", {
				"type": "renter",
				# Type is one of [owner,renter] -- owner means rentals on your rigs, renter means rentals you purchased
				# "algo": "",			#Filter by algo, see /info/algos
				"history": historical,  # true = Show completed rentals, false = Active rentals
				# "rig": ,			#Show rentals related to a specific rig ID
				"start": offset,  # Start number (for pagination)
				"limit": 25,  # Limit number (for pagination)
				# "currency": ""		#Filter by rentals paid currency, one of (BTC,LTC,ETH,DOGE)
			}))
			if not result['success']: return False
			for rentalData in result['data']['rentals']:
				rentals.append(Rental(self, rentalData))
			if len(result['data']['rentals']) < 25:
				finished = True
			offset += 25

		'''
		{
			"success": True,
			"data": {
				"total": "1",
				"returned": 1,
				"start": 0,
				"limit": 25,
				"rentals": [
					{
						"id": "4562983",
						"owner": "Titan19",
						"renter": "FelixRom",
						"hashrate": {
							"advertised": {"hash": "90", "type": "th", "nice": "90.00T"},
							"average": {
								"hash": "239.11218195115",
								"type": "th",
								"nice": "239.11T",
								"percent": "265.68",
							},
						},
						"price": {
							"type": "legacy",
							"advertised": "0.00000000",
							"paid": "0.00001035",
							"currency": "BTC",
						},
						"price_converted": {
							"type": "th",
							"advertised": "0.00000092",
							"currency": "BTC",
						},
						"length": "3",
						"extended": "0",
						"extensions": [],
						"start": "2024-06-17 09:06:34 UTC",
						"end": "2024-06-17 12:06:34 UTC",
						"start_unix": "1718615194",
						"end_unix": "1718625994",
						"ended": False,
						"rig": {
							"id": "222067",
							"name": "AvBLIK",
							"owner": "Titan19",
							"type": "sha256ab",
							"status": {
								"status": "rented",
								"hours": "2.9358",
								"rented": True,
								"online": True,
								"rental_id": "4562983",
							},
							"online": True,
							"xnonce": "no",
							"poolstatus": "online",
							"region": "eu-ru",
							"rpi": "96.17",
							"suggested_diff": "132",
							"optimal_diff": {"min": "209547.579", "max": "1257285.476"},
							"ndevices": "1",
							"device_memory": None,
							"extensions": True,
							"price": {
								"type": "th",
								"BTC": {
									"currency": "BTC",
									"price": "0.00000092",
									"hour": "0.000003450000",
									"minhrs": "0.00001035",
									"maxhrs": "0.00004140",
									"min_rental_length": 0,
									"enabled": True,
								},
								"LTC": {
									"currency": "",
									"price": 0,
									"hour": 0,
									"minhrs": 0,
									"maxhrs": 0,
									"min_rental_length": 0,
									"enabled": False,
								},
								"DASH": {
									"currency": "",
									"price": 0,
									"hour": 0,
									"minhrs": 0,
									"maxhrs": 0,
									"min_rental_length": 0,
									"enabled": False,
								},
								"ETH": {
									"currency": "",
									"price": 0,
									"hour": 0,
									"minhrs": 0,
									"maxhrs": 0,
									"min_rental_length": 0,
									"enabled": False,
								},
								"BCH": {
									"currency": "",
									"price": 0,
									"hour": 0,
									"minhrs": 0,
									"maxhrs": 0,
									"min_rental_length": 0,
									"enabled": False,
								},
								"DOGE": {
									"currency": "",
									"price": 0,
									"hour": 0,
									"minhrs": 0,
									"maxhrs": 0,
									"min_rental_length": 0,
									"enabled": False,
								},
							},
							"minhours": "3",
							"maxhours": "12",
							"hashrate": {
								"advertised": {"hash": 90, "type": "th", "nice": "90.00T"},
								"last_5min": {
									"hash": "86759648.449",
									"type": "mh",
									"nice": "86.76T",
								},
								"last_15min": {
									"hash": "85293064.086",
									"type": "mh",
									"nice": "85.29T",
								},
								"last_30min": {
									"hash": "95637322.437",
									"type": "mh",
									"nice": "95.64T",
								},
							},
							"error_notice": None,
							"description": "",
							"available_status": "available",
							"shorturl": "http://rig.rent/rigs/222067",
							"device_ram": "0",
						},
						"was_refunded": False,
						"more": [],
					}
				],
			},
		}
		'''

		return rentals
	def getRentalDataByID(self, id):
		result = json.loads(self.get("/rental/"+str(id)))
		if not result['success']: return False
		return result['data']

#/account/profile
	def getPoolProfiles(self):
		result = json.loads(self.get("/account/profile"))
		if not result['success']: return False
		return result['data']
	def createPoolProfile(self, name):
		result = json.loads(self.put("/account/profile", {'name': name,'algo': self.algo}))
		if not result['success']: return False
		return result['data']['id']
	def deletePoolProfile(self, profileID):
		result = json.loads(self.delete("/account/profile/"+str(profileID)))
		if not result['success']: return False
	def addPoolToProfile(self, profileID, poolID, priority):
		result = json.loads(self.put("/account/profile/" + str(profileID),{'poolid':poolID,'priority':priority}))
		if not result['success']: return False
		return result['data']
	def printPoolProfiles(self): #returns pool profiles created in the user account
		profiles = self.getPoolProfiles()

		print(str(len(profiles))+' Account Profile(s) found:')
		for profile in profiles:
			id = profile['id']
			name = profile['name']
			algo = profile['algo']['name']
			pools = profile['pools']
			if not pools: pools = []

			print('ID: '+id)
			print('\tName: '+name)
			print('\tAlgo: '+algo)
			print('\t'+str(len(pools))+ ' pool(s): ')
			for pool in pools:
				print('\t\t'+str(pool))

			print('')

#/account/pool
	def getPools(self):
		result = json.loads(self.get("/account/pool"))
		if not result['success']: return False
		return result['data']
	def addPool(self, name, host, port, user, password):
		result = json.loads(self.put("/account/pool",{'type':self.algo, 'name':name, 'host': host, 'port': port, 'user': user, 'pass': password}))
		if not result['success']: return False
		return result['data']['id']
	def deletePool(self, id):
		result = json.loads(self.delete("/account/pool/"+str(id)))
		if not result['success']: return False
		return result['data']
	def printPools(self):
		pools = self.getPools()
		print(str(len(pools))+' Pool(s) found:')
		for pool in pools:
			print(pool)

#/rig
	def getRigsData(self, lowestHashrateTH=0):
		# Request all rigs from all pages
		finished = False
		offset = 0
		rigsData = []
		while not finished:
			result = json.loads(self.get("/rig", {
				'type': self.algo,
				'orderby': 'price',
				'count': 100,
				'offset': offset,
				'hash.min': int(lowestHashrateTH),
				'hash.type': 'th'
			}))
			if not result['success']: return False
			for rigData in result['data']['records']:
				rigsData.append(rigData)
			if len(result['data']['records']) < 100:
				finished = True
			offset += 100

		return rigsData
	def getRigs(self, lowestHashrateTH=0):
		rigs = []
		for rigData in self.getRigsData(lowestHashrateTH):
			rigs.append(Rig(self,rigData))
		return rigs
	def getRigDataByID(self,id):
		result = json.loads(self.get("/rig/"+str(id)))
		if not result['success']: return False
		return result['data']
	def getRigByID(self, id):
		return Rig(self, self.getRigDataByID(id))
	def getCheapestRigFor3Hours(self):
		for rig in self.getRigs():
			if rig.minHours == "3":
				return rig
class Rig:
	def __init__(self, mrr, data):
		'''{
			"id": "284932",
			"name": "Avalon pro s 123th",
			"owner": "nnp0919",
			"type": "sha256ab",
			"status": {"status": "available", "hours": 0, "rented": False, "online": True},
			"online": True,
			"xnonce": "yes",
			"poolstatus": "online",
			"region": "eu-de",
			"rpi": "new",
			"suggested_diff": "",
			"optimal_diff": {"min": "286381.692", "max": "1718290.150"},
			"ndevices": "1",
			"device_memory": None,
			"extensions": True,
			"price": {
				"type": "th",
				"BTC": {
					"currency": "BTC",
					"price": "0.00019200",
					"hour": "0.000983999996",
					"minhrs": "0.00295200",
					"maxhrs": "0.23616000",
					"min_rental_length": 0,
					"enabled": True,
				},
				"LTC": {
					"currency": "",
					"price": 0,
					"hour": 0,
					"minhrs": 0,
					"maxhrs": 0,
					"min_rental_length": 0,
					"enabled": False,
				},
				"DASH": {
					"currency": "",
					"price": 0,
					"hour": 0,
					"minhrs": 0,
					"maxhrs": 0,
					"min_rental_length": 0,
					"enabled": False,
				},
				"ETH": {
					"currency": "",
					"price": 0,
					"hour": 0,
					"minhrs": 0,
					"maxhrs": 0,
					"min_rental_length": 0,
					"enabled": False,
				},
				"BCH": {
					"currency": "",
					"price": 0,
					"hour": 0,
					"minhrs": 0,
					"maxhrs": 0,
					"min_rental_length": 0,
					"enabled": False,
				},
				"DOGE": {
					"currency": "",
					"price": 0,
					"hour": 0,
					"minhrs": 0,
					"maxhrs": 0,
					"min_rental_length": 0,
					"enabled": False,
				},
			},
			"minhours": "3",
			"maxhours": "240",
			"hashrate": {
				"advertised": {"hash": 123, "type": "th", "nice": "123.00T"},
				"last_5min": {"hash": "124516276.004", "nice": "124.52T", "type": "mh"},
				"last_15min": {"hash": "96845992.448", "nice": "96.85T", "type": "mh"},
				"last_30min": {"hash": "98103732.684", "nice": "98.10T", "type": "mh"},
			},
			"error_notice": None,
			"description": "ATTENTION: SLUSHPOOL may NOT WORK",
			"available_status": "available",
			"shorturl": "http://rig.rent/rigs/284932",
			"device_ram": "0",
		}
'''
		self.data = data
		self.mrr = mrr
		self.id = data['id']
		self.name = data['name']
		self.priceType = data['price']['type']
		self.priceHour = data['price']['BTC']['hour']
		self.price = float(data['price']['BTC']['price']) * 1000 * 1000 # BTC/EH/day
		self.minHours = data['minhours']
		self.maxHours = data['maxhours']
		self.minRentalLength = data['price']['BTC']['min_rental_length']

		self.hashrate_advertised_eh = float(data['hashrate']['advertised']['hash']) / 1000 / 1000
		self.hashrateType = data['hashrate']['advertised']['type']

		if data['hashrate']['advertised']['type'] != "th": print("Achtung! Nicht auf TH bezogen. Bitte prüfen. Falsche Werte!")
		if 'price' in data and data['price']['type'] == "th":
			self.price = float(data['price']['BTC']['price']) * 1000 * 1000 #btc/eh/day
		else:
			print("Achtung! Preis nicht auf TH bezogen. Bitte prüfen. Falsche Werte!")

		mrr.allRigs[self.id] = self
	def reload(self): #Reloads all rig data from the API
		data = self.mrr.getRigDataByID(self.id)
		self.__init__(self.mrr, data)

	def info(self):
		result = json.loads(self.mrr.get("/rig/"+str(self.id)))
		'''{
			"success": True,
			"data": {
				"id": "322406",
				"name": "S19_Garage03",
				"owner": "Kolegio",
				"type": "sha256ab",
				"status": {"status": "available", "hours": 0, "rented": False, "online": True},
				"online": True,
				"xnonce": "no",
				"poolstatus": "nopool",
				"region": "eu-ru",
				"rpi": "new",
				"suggested_diff": "",
				"optimal_diff": {"min": "232830.644", "max": "1396983.862"},
				"ndevices": "1",
				"device_memory": None,
				"extensions": True,
				"price": {
					"type": "th",
					"BTC": {
						"currency": "BTC",
						"price": "0.00000094",
						"hour": "0.000003916667",
						"minhrs": "0.00001175",
						"maxhrs": "0.00037600",
						"min_rental_length": 0,
						"enabled": True,
					},
					"LTC": {
						"currency": "",
						"price": 0,
						"hour": 0,
						"minhrs": 0,
						"maxhrs": 0,
						"min_rental_length": 0,
						"enabled": False,
					},
					"DASH": {
						"currency": "",
						"price": 0,
						"hour": 0,
						"minhrs": 0,
						"maxhrs": 0,
						"min_rental_length": 0,
						"enabled": False,
					},
					"ETH": {
						"currency": "",
						"price": 0,
						"hour": 0,
						"minhrs": 0,
						"maxhrs": 0,
						"min_rental_length": 0,
						"enabled": False,
					},
					"BCH": {
						"currency": "",
						"price": 0,
						"hour": 0,
						"minhrs": 0,
						"maxhrs": 0,
						"min_rental_length": 0,
						"enabled": False,
					},
					"DOGE": {
						"currency": "",
						"price": 0,
						"hour": 0,
						"minhrs": 0,
						"maxhrs": 0,
						"min_rental_length": 0,
						"enabled": False,
					},
				},
				"minhours": "3",
				"maxhours": "96",
				"hashrate": {
					"advertised": {"hash": 100, "type": "th", "nice": "100.00T"},
					"last_5min": {"hash": "0.000", "type": "mh", "nice": "0.00"},
					"last_15min": {"hash": "0.000", "type": "mh", "nice": "0.00"},
					"last_30min": {"hash": "0.000", "type": "mh", "nice": "0.00"},
				},
				"error_notice": None,
				"description": "",
				"available_status": "available",
				"shorturl": "http://rig.rent/rigs/322406",
				"device_ram": "0",
			},
		}
		'''
		if not result['success']: return False
		print(result)
	def rent(self, duration):
		result = json.loads(self.mrr.put("/rental",{
			"rig": self.id,						#Rig ID to rent
			"length": duration,					#Length in hours to rent
			"profile": self.mrr.poolProfileID,		#The profile ID to apply (see /account/profile
			"rate.type": "th",					#The hash type of rate. defaults to "mh", possible values: [hash,kh,mh,gh,th]
			# "currency": "BTC",				#Currency to use -- one of [BTC,LTC,ETH,DOGE]
			#"rate.price": 25,					#Price per [rate.type] per day to pay -- this is a filter only, it will use the rig's current price as long as it is <= this value
		}))
		if not result['success']:
			print(result)
			return False
		self.rentalid = result['data']['id']
		return result

	def getProfitFactor(self, breakEvenPoint):
		if self.price == 0:
			return 0.0
		else:
			return breakEvenPoint / self.price
	def getProfitability(self, breakEvenPoint):
		if self.price == 0:
			return 0.0
		else:
			return (self.getProfitFactor(breakEvenPoint)-1)*100
class Rental:
	def __init__(self, mrr, data):
		if data['hashrate']['advertised']['type'] != "th": print("Achtung! Nicht auf TH bezogen. Bitte prüfen. Falsche Werte!")
		if data['hashrate']['average']['type'] != "th": print("Achtung! Nicht auf TH bezogen. Bitte prüfen. Falsche Werte!")
		self.data = data
		self.mrr = mrr
		self.id = data['id']
		self.owner = data['owner']
		self.renter = data['renter']
		self.hashrate_advertised_eh = float(data['hashrate']['advertised']['hash']) / 1000 / 1000
		self.hashrate_average_eh = float(data['hashrate']['average']['hash']) / 1000 / 1000
		self.rig = self.mrr.getRigByID(data['rig']['id'])
		self.pricePaid = float(data['price']['paid'])
		self.price = float(data['price_converted']['advertised']) *1000 * 1000 # !!! added
		self.timestampStart = int(data['start_unix'])
		self.timestampEnd = int(data['end_unix'])
		self.rentalFinished = data['ended']
		'''
		{
			"id": "4562983",
			"owner": "Titan19",
			"renter": "FelixRom",
			"hashrate": {
				"advertised": {"hash": "90", "type": "th", "nice": "90.00T"},
				"average": {
					"hash": "239.11218195115",
					"type": "th",
					"nice": "239.11T",
					"percent": "265.68",
				},
			},
			"price": {
				"type": "legacy",
				"advertised": "0.00000000",
				"paid": "0.00001035",
				"currency": "BTC",
			},
			"price_converted": {
				"type": "th",
				"advertised": "0.00000092",
				"currency": "BTC",
			},
			"length": "3",
			"extended": "0",
			"extensions": [],
			"start": "2024-06-17 09:06:34 UTC",
			"end": "2024-06-17 12:06:34 UTC",
			"start_unix": "1718615194",
			"end_unix": "1718625994",
			"ended": False,
			"rig": {
				"id": "222067",
				"name": "AvBLIK",
				"owner": "Titan19",
				"type": "sha256ab",
				"status": {
					"status": "rented",
					"hours": "2.9358",
					"rented": True,
					"online": True,
					"rental_id": "4562983",
				},
				"online": True,
				"xnonce": "no",
				"poolstatus": "online",
				"region": "eu-ru",
				"rpi": "96.17",
				"suggested_diff": "132",
				"optimal_diff": {"min": "209547.579", "max": "1257285.476"},
				"ndevices": "1",
				"device_memory": None,
				"extensions": True,
				"price": {
					"type": "th",
					"BTC": {
						"currency": "BTC",
						"price": "0.00000092",
						"hour": "0.000003450000",
						"minhrs": "0.00001035",
						"maxhrs": "0.00004140",
						"min_rental_length": 0,
						"enabled": True,
					},
					"LTC": {
						"currency": "",
						"price": 0,
						"hour": 0,
						"minhrs": 0,
						"maxhrs": 0,
						"min_rental_length": 0,
						"enabled": False,
					},
					"DASH": {
						"currency": "",
						"price": 0,
						"hour": 0,
						"minhrs": 0,
						"maxhrs": 0,
						"min_rental_length": 0,
						"enabled": False,
					},
					"ETH": {
						"currency": "",
						"price": 0,
						"hour": 0,
						"minhrs": 0,
						"maxhrs": 0,
						"min_rental_length": 0,
						"enabled": False,
					},
					"BCH": {
						"currency": "",
						"price": 0,
						"hour": 0,
						"minhrs": 0,
						"maxhrs": 0,
						"min_rental_length": 0,
						"enabled": False,
					},
					"DOGE": {
						"currency": "",
						"price": 0,
						"hour": 0,
						"minhrs": 0,
						"maxhrs": 0,
						"min_rental_length": 0,
						"enabled": False,
					},
				},
				"minhours": "3",
				"maxhours": "12",
				"hashrate": {
					"advertised": {"hash": 90, "type": "th", "nice": "90.00T"},
					"last_5min": {
						"hash": "86759648.449",
						"type": "mh",
						"nice": "86.76T",
					},
					"last_15min": {
						"hash": "85293064.086",
						"type": "mh",
						"nice": "85.29T",
					},
					"last_30min": {
						"hash": "95637322.437",
						"type": "mh",
						"nice": "95.64T",
					},
				},
				"error_notice": None,
				"description": "",
				"available_status": "available",
				"shorturl": "http://rig.rent/rigs/222067",
				"device_ram": "0",
			},
			"was_refunded": False,
			"more": [],
		}
		'''
	def reload(self): #Reloads all rental data from the API
		data = self.mrr.getRentalDataByID(self.id)
		self.__init__(self.mrr, data)

	def extend(self, durationHours):
		result = json.loads(self.mrr.put("/rental/" + str(self.id) + '/extend', {
			"length": durationHours,  # Length in hours to rent
		}))
		if not result['success']:
			print(result)
			return False
		self.rig.reload()
		self.reload()
		return result
	def getGraphData(self):
		result = json.loads(self.mrr.get("/rental/" + str(self.id) + '/graph'))
		if not result['success']:
			print(result)
			return false
		'''{
			"success": True,
			"data": {
				"rentalid": "4563411",
				"rigid": "270384",
				"chartdata": {
					"time_start": "2024-06-17 16:22:52",
					"time_end": "2024-06-17 19:22:52",
					"timestamp_start": "1718655772",
					"timestamp_end": "1718666572",
					"bars": "[1718655780000,0],[1718655840000,0],[1718655900000,32213209157177],[1718655960000,24461905703731]",
					"average": "[1718655780000,0],[1718655840000,0],[1718655900000,32213209157177],[1718655960000,24461905703731]",
					"rejected": "[1718655780000,0],[1718655840000,0],[1718655900000,0],[1718655960000,0]",
					"rentals": "none",
					"offline": "none",
					"pooloffline": "none",
				},
				"hashtype": "th",
				"advertised": {"raw": "100000000000000.000", "hashtype": 100},
			},
		}'''
		chartData = json.loads('['+result['data']['chartdata']['bars']+']')
		chartData = [[x[0], self.price, x[1]] for x in chartData] #!!!
		chartData = np.array(chartData)
		sumed_hashrate = sum(chartData[:, 2])
		chartData[:, 2] = np.cumsum(chartData[:, 2]) * (self.pricePaid / sumed_hashrate * 100000000)
		return chartData, json.loads(result['data']['chartdata']['timestamp_start']), json.loads(result['data']['chartdata']['timestamp_end'])
	def getPools(self):
		result = json.loads(self.mrr.get("/rental/" + str(self.id) + '/pool'))
		if not result['success']:
			print(result)
			return False
		return result['data']
	def setPoolProfile(self, profileID):
		result = json.loads(self.mrr.put("/rental/" + str(self.id) + '/profile', {'profile':profileID}))
		if not result['success']:
			print(result)
			return False
		return result
class FullDay:
	def __init__(self, mrr, date):
		self.mrr = mrr
		self.date = date
		self.zipPath = mrr.path_data_compressed + self.date + '.zip'
		self.data = self.getZipData()
		self.timestamps = sorted(self.data.keys())

		self.blocks = self.getBlocks()
		self.averageFee = self.getAverageFee()


# General
	def getBreakEvenPoint(self, timestamp):
		blockHeight, blockTimestamp, blockFees, blockDifficulty = self.mrr.getLastBlockFromTimestamp(timestamp)
		hashratePercent = 1 / getHashRateFromDifficulty(blockDifficulty)
		averageTotalRewardsPerBlock = self.mrr.block_reward + (self.averageFee / 100000000)
		totalRewardsPerBlock = averageTotalRewardsPerBlock * hashratePercent
		totalRewardsFullDay = totalRewardsPerBlock * 6 * 24

		return totalRewardsFullDay * 0.97 * 0.9976  # 3% MRR fee & 0.24% pool fee
	def getNextTimestamp(self, timestamp):
		for i in range(len(self.timestamps) - 1):
			current_timestamp = self.timestamps[i]
			next_timestamp = self.timestamps[i + 1]
			if int(current_timestamp) == int(timestamp):
				return next_timestamp
		return False

# Blockchain
	def getBlocks(self):
		return self.mrr.getBlocks(self.date)
	def getAverageFee(self):
		fees_only = [row[2] for row in self.blocks]
		fees_average = sum(fees_only) / len(fees_only)
		return fees_average

# ZIP
	def getZipData(self):
		with zipfile.ZipFile(self.zipPath, 'r') as zfile:
			zfile.extractall(self.mrr.path_temp)

		for filename in os.listdir(self.mrr.path_temp):
			file_path = os.path.join(self.mrr.path_temp, filename)
			if os.path.isfile(file_path) and file_path.endswith('.json'):
				with open(file_path, 'r') as file:
					data = json.load(file)
				shutil.rmtree(self.mrr.path_temp)
				return data
class Snapshot:
	def __init__(self, day, timestamp):
		self.day = day
		self.data = self.day.data[timestamp]
		self.timestamp = int(timestamp)
		self.nextTimestamp = int(day.getNextTimestamp(self.timestamp))
		self.periodDurationDays = (self.nextTimestamp - self.timestamp) / 60 / 60 / 24
		self.breakEvenPoint = day.getBreakEvenPoint(timestamp)