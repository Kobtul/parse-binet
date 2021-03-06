# parse-binet
This script parses binetflows and produces the json file with extracted features. This tool uses binetflows generated by Argus. https://qosient.com/argus/
## Getting Started
First we need to get Argus bintflows to use our tool. We can use ones from the public datasets like this: https://stratosphereips.org/category/dataset.html or we can generate our own by using Argus as described bellow.
Once we have the binetflows we can run the python script to generate the profiles and save them to the JSON file.
## Argus configuration
The argus config file is located in argusconf/argus_bi.conf, the ra config file is located in argusconf/ra.conf
The parameters for running argus are:
```
argus -r pcapfile -F argus_bi.conf -w file.biargus
```
once we have the biargus file, we can use ra to obtain the flows, like this
```
ra -Z b -n -r file.biargus -F ra.conf > file.binetflow
```
if we want to specify hosts that will be in the binetflow, we can use this variant:
```
ra -Z b -n -r file.biargus -F ra.conf - "host A or host B or ...." > file.binetflow

```

## Profiles generation
To run the dataGather.py script you need to specify these two global variables:
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
