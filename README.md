# Guide for metacore
**metacore** is an console utility which serve data of an remote user in your machine.
**metacore** represent a python package. You can install with next command:

    $ python setup.py install

and then run the test suite:

    $ python setup.py test
    
After the installation you can run the app with command `metacore` in the terminal:

    $ metacore
    ...
    
---

## docker and metacore
The **metacore** pachage is contains **Dockerfile**, so you can use `docker` to build and run in like the container.
In the terminal open the pachage dir where the **Dorkerfile** is and run the next command to build the container:

    docker build --tag="metacore" --rm=true .

After building process run new container with the next command:

    $ docker run -idtp 5000:5000 --name="metacore" metacore
    60faa95f94bc322b4f0409a41f4ebb35b7203acc047071797f8ca7fee6a72d57

This one will run container in the background mode. `60faa95f9...` is the hash of the runned process. 
You can use it for stop or fetch the container from the background mode:

    $ # next command will stop the running
    $ docker rm -f 60faa95f9
    60faa95f9
    
    ...
    $ # this is return control over the container
    $ docker attach f2f8e752043d
    
    ...
    $ # such as this one
    $ docker attach metacore

If you want remove the container at all, stop in first and then enter next command:

    $ docker rm -f metacore
    metacore
    $ docker rmi metacore
    Untagged: metacore:latest
    Deleted: 9bc28da47ab2cf4c00e05940dbdf33552cd7aa5334017d95b21c58a0d8d99715
    Deleted: dafeb11c5a25f350722871b02c4a319dba2452c909c6c82fbcccc3311bc9e2b1
    Deleted: 78a99e9b3143697990ed406b543d53dcd11fe5948468e011fc9cfb75ffbd6038
    Deleted: befa486bee6a2e846a23bd251ddc4f9e36f5638a5afa7089b3a284c4759eb2f2
    Deleted: b17053ce0c4c96c123fd6e1b0369b11609f77d2e6ee1e549b0983f106f528d52
    Deleted: 27342527ac04d69bb988eb134cd76ec23870a7d21b379ce935135b6d7da8832f
    Deleted: 8dc53b0ce7a0ce52e62d1a5ac2288cb6836d78b11cc876e6e2d254e764d0b414
    Deleted: e9558034e70fbe75fd2accc28d1f25b1d57e9071466b3b876016a53808b8fbee
    Deleted: 04b209dc24f67d347988e27a3dfac2e581ac7155dbfb1e01207cda6f5aed3c6f
    Deleted: 67bb5fb78e0029a9c0f8a5a0895d9ad3c8068ff759ad48c94609b9c4ad637f3e
    Deleted: bd47abde49c1190bf01cb258fa7ca4c70a4d630743a5c789a25eae876a511584
    Deleted: 2b86a1827d384d397072f2c3baaa72c3e64986403697913e813581de32dd1c58
    Deleted: b822f08e9c20bc9f42f167fbb120518bac784879ee70e5f359a94c1d921c5a97
