# SRF Auto Setup

Please refer to https://confluence.slac.stanford.edu/display/SRF/SRF+Auto+Setup for the most up to date documentation


## Installation and Setup Instructions

These instructions were made using an Ubuntu Bionic distribution, instructions for other flavours of linux may vary.


---------------------------------

### Packages to Install

The dependencies for this project can be installed by running the following command:

```apt install git python3.8 python3-pip libxcb-xinerama0```



---------------------------------


### Repositories to Clone

The following repositories are required for this project:

- [EPICS base](https://github.com/epics-base)
- [LCLS Tools](https://github.com/slaclab/lcls-tools)
- [Simulacrum](https://github.com/slaclab/simulacrum)

Cloning of the above repositories can be done using the following commands:

```
git clone https://github.com/slaclab/lcls-tools.git
git clone https://github.com/slaclab/simulacrum.git
git clone --recursive -b 7.0 https://git.launchpad.net/epics-base base-7.0

```


---------------------------------


### Builing EPICS Base 7.0

To build EPICS base, go into the cloned directory for epics and run the following commands:

```
make configure
make
make install
```

This may take some time to finish building. Once completed, you can add the created binaries to your path by running:

```export PATH=$PATH:<location_of_epics>/bin/linux-x86_64/```

This can be verified by running `caget` from any location, it should report that a PV was not specified in the command.


---------------------------------


### Seting Up Python Packages

LCLS Tools
==========

You will also need to install some python packages for this project, the LCLS Tools package can be installed from source by going into the cloned directory for LCLS Tools and running:

```python3.8 -m pip install ```

This will add the LCLS Tools packages to the dist-packages location for python3.8. To allow python to see this package you will need to add the dist-packages location to the `PYTHONPATH` environment variable by running:

``` export PYTHONPATH=$PYTHONPATH:/lib/python38/dist-packages```

This can be verified by starting a python interpreter (using the `python3.8` command) and importing lcls-tools:

``` import lcls-tools```

If you do not receive an ModuleImportError then the package has been found.


Other Packages
==============

The remaining dependencies do not need to be installed from source, so we can use pip to install them from the package registries:

```
python3.8 -m pip install setuptools
python3.8 -m pip install --upgrade pip setuptools
python3.8 -m pip install pyqt5 pydm p4p caproto

```

Finally, for the SRF Auto Setup GUI we will need to define an environment variable for using pydm.

```export PYDM_DEFAULT_PROTOCOL=ca```


---------------------------------


## Running the sc_rf_service on Simulacrum

Running the sc_rf_service on the simulacrum for this project can be done by going into the cloned directory for the simulacrum and running the following command (this should either be done in separate tab, or using a background process that can be killed later using `ps` to find the process ID and running `kill <process-id>`)

```python3.8 ./sc_rf_service/sc_rf_service.py```

Once the service has started, we can run the SRF Auto Setup GUI.

---------------------------------

## Running SRF Auto Setup

To run the SRF Auto Setup GUI, go into the cloned location for this repository and run:

```pydm setup_gui.py```

The GUI should open up and be ready for use.





