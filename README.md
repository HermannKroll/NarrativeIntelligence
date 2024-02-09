# Narrative Service
This repository contains the code and scripts for PubPharm's [Narrative Service](www.narrative.pubpharm.de). 
[PubPharm](www.pubpharm.de) is a platform of the specialized information service for pharmacy (Fachinformationsdient Pharmazie). 

If you want to know details about the service, we refer the reader to [our following paper](https://doi.org/10.1007/s00799-023-00356-3):
```
@article{kroll2023discovery,
  title={A discovery system for narrative query graphs: entity-interaction-aware document retrieval},
  author={Kroll, Hermann and Pirklbauer, Jan and Kalo, Jan-Christoph and Kunz, Morris and Ruthmann, Johannes and Balke, Wolf-Tilo},
  journal={International Journal on Digital Libraries},
  pages={1--22},
  year={2023},
  publisher={Springer},
  doi={10.1007/s00799-023-00356-3}
}
```
If you use our service for your own research, please cite the previous paper. 
Thank you.

# Structure
The project consists of two parts.
Make sure which part you want to setup and run:
- Narrative Service (see [Readme](README_Service.md))
- Mining scripts to update the service data (see [Readme](README_Mining.md))


# Development

## Setting up the Test Suite
Just execute src/nitests folder via pytests.

## SSH Server Interpreter
Check out the latest version of the project. 
Next open the project in PyCharm.
Next, configure the SSH Interpreter in PyCharm. 
Python Interpreter can be found in the local conda directory (.conda/...)


## General Database Schema
![DB Scheme](./docs/dbdiagram.png)

## Narrative Service Database Schema
![DB Scheme](./docs/dbdiagram_service.png)

