# parse-binet
This script parses binetflows and produces the json file with extracted features
## Getting Started
To run the dataGather.py script you need to have file fileToAnalyze.py that contains:
```
COMPUTERSTOANALYZER = 'adress of the file with computers to analyze'
BINETFLOW = 'adress to binetflows'
```

The compurers to analyze file structure is:
```
IP1:information about ip1
IP2:information about ip2
...
```
The information about ip can be blanc.
In the dataGather where are two boolean configs avaible:
```
USEWHOISDATA turns on or off gathering the whois data.
SAVECACHE turns on or off saving the whois data cache.
```
