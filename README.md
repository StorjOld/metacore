# metacore

[![Build Status](https://travis-ci.org/Storj/metacore.svg?branch=master)](https://travis-ci.org/Storj/metacore)
[![Coverage Status](https://coveralls.io/repos/Storj/metacore/badge.svg?branch=master&service=github)](https://coveralls.io/github/Storj/metacore?branch=master)
[![License](https://img.shields.io/badge/license-AGPL%20License-blue.svg)](https://github.com/Storj/metacore/blob/master/LICENSE)

**metacore** is an console utility which serves the data of an remote user in your machine.
**metacore** represents a python package. You can install it with the next command:

    $ python setup.py install

and then run the test suite:

    $ python setup.py test
    
After the installation you can run the app with the command `metacore` in the terminal:

    $ metacore
    ...

---

## docker and metacore

The **metacore** package contains **Dockerfile**, so you can use `docker` to build and run it like the docker container.
This container is like some small isolated UNIX instance, customized with respect to the ``Dockerfile`` logic.
In the terminal open the package dir, where the **Dockerfile** is and run the next command to build the **image**:

    # enter such a command to build the image for a future running container on it
    $ docker build --tag="metacore_image" --rm=true .
    ...
    Step 17 : ENTRYPOINT //start.sh
     ---> Running in 656f1a4e8f2a
     ---> c20f75716420
    Removing intermediate container 656f1a4e8f2a
    Successfully built c20f75716420
    
    # Or pass the repository addres where the ``Dockerfile`` is.
    # In our case is git@github.com:Storj/metacore
    $ docker build --tag="metacore_image" --rm=true git@github.com:Storj/metacore
    
    ...
   
> Note: The ``.`` in the end of first example is required - it provides the current directory-name value, where to look for the **Dockerfile**.
        ``--rm=true`` - This key apply removing intermediate containers after the successful build.
        
New **image** will be created under the **"metacore_image"** name:
 
    $ docker images
    REPOSITORY          TAG                 IMAGE ID            CREATED             VIRTUAL SIZE
    metacore_image      latest              83812a9d4386        4 minutes ago       428.9 MB
    ubuntu              14.04               6cc0fc2a5ee3        5 days ago          187.9 MB

After building process run the new container with the next command:

    $ docker run -idt -p 5000:5000 --name="metacore_container" metacore_image
    60faa95f94bc322b4f0409a41f4ebb35b7203acc047071797f8ca7fee6a72d57

Last command will run container in the background mode. `60faa95f9...` is the hash of the runned process:

    # Show all docker's containers
    $ docker ps -a
    CONTAINER ID        IMAGE               COMMAND             CREATED              STATUS              PORTS                    NAMES
    60faa95f94bc        metacore_image      "//start.sh"        About a minute ago   Up About a minute   0.0.0.0:5000->5000/tcp   metacore_container

We've set the translation of the 5000 port with ``-p 5000:5000`` key from the container. So your localhost:5000 port was bound to the 5000
container's port.
You can control this container - stop or fetch it from the background mode:

    ...
    # this will return control over the container
    $ docker attach 60faa95f94bc
    
    root@60faa95f94bc://root/metacore# 
    
    ...
    # such as this one
    $ docker attach metacore
    ...
    
> Note: When attaching or running this container (but, not in detached mode) you will get the control over the container's terminal
        (like with ssh access). If nothing is show after the command's enter, you should press "Enter"
        to see the container's terminal invitation.
        
Container's **bash** is similar but restricted in set of commands, nevertheless required one can be installed manually.
So, when you got the access to the container you can execute whatever actions you want to:

    root@60faa95f94bc://root/metacore# pwd
    //root/metacore
    root@60faa95f94bc://root/metacore# ls
    build  dist  Dockerfile  LICENSE  MANIFEST.in  metacore  metacore.egg-info  metacore_nginx_config  metacore_uwsgi.ini  README.md  setup.py  start.sh  static  uwsgi.log
    root@60faa95f94bc://root/metacore# vi metacore/Blacklist.txt
    ...

As you can see, the current working directory is ``//root/metacore`` by default. This is where MetaCore's source code is nested in the container.

To leave the container session and don't stop the process of running, use the escape sequence Ctrl-p + Ctrl-q,
or print ``exit`` to stop it and exit:

    root@60faa95f94bc://root/metacore# exit
    exit
    jeka@jeka-from-ua:~/$ 
    jeka@jeka-from-ua:~/$ $ docker ps -a
    CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS                       PORTS               NAMES
    60faa95f94bc        metacore_image       "//start.sh"        54 minutes ago      Exited (127) 4 seconds ago                       metacore_container

If container was stopped you can **start** it again:

    jeka@jeka-from-ua:~/$ docker start metacore_container 
    metacore_container
    jeka@jeka-from-ua:~/$ docker ps -a
    CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS                    NAMES
    60faa95f94bc        metacore_image       "//start.sh"        About an hour ago   Up 2 seconds        0.0.0.0:5000->5000/tcp   metacore_container


Delete container this way:

    # next command will delete the container and force stop it it it's running:
    $ docker rm -f 60faa95f9
    60faa95f9
    

If you want to remove the **image** too, stop and delete all related **containers** first, and then enter the next command:

    # force delete container
    jeka@jeka-from-ua:~/$ docker rm -f metacore_container 
    metacore_container
    
    # delete image
    jeka@jeka-from-ua:~/$ docker rmi metacore_image
    Untagged: metacore_image:latest
    Deleted: c20f75716420b65f40f45d2c5a2bea127eb2b781b67019003b47aeae36380c2e
    Deleted: 258cdac0eab4c9b9d570c323f3a97c211abe94a61b86d4bf9df4b8b8f4e88394
    Deleted: ababff883575a0a71b2c8d803fddd47bc42a84ac05b4872e3ba42eb58c353800
    Deleted: 2511ade2e94b0257b27f5f0856149c5c5dfda21f3d86aac365b1a5db31c37e73
    Deleted: fb3a05e1fe550e373715624dc771216c1d11649b7eb40fffe233b4a618693361
    Deleted: a4f14f0c36a833859bd846898dcb56600f09090ae3897b7923b95569ba1cb69d
    Deleted: efbaed4acf3a53aa167ec04e9d12d4cd7814bf67a191e2e1d59158a7788f28e8
    Deleted: 5223a2c05331b79453869ead368e413742dd4d833030b36df570ebcf21945ac1
    Deleted: c7c728090fab05aa4143a55dbefe6144ac4171fb53c16b9cd200b536736f1be7
    Deleted: 60986ed719fcaa984c99ba67598beee645da43a0f0696dcd83709247d9f1d73c
    Deleted: b95e96f1c23367742a37f86d41238ea6b15071a27eff32601da0089198766375
    Deleted: 2a8979fe96ffde8b4fe1e5f6692e50f35ce5b5884539e6f8e5406789e28efeb8
