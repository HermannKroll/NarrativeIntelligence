
## Enable GPU Support for Training (PyTorch)
First switch to conda prompt in env

Find your installed Cuda Version 
	cat /usr/local/cuda/version.txt

Coda Version 9

        conda install pytorch torchvision cudatoolkit=9.0 -c pytorch  

Cuda Version 10:

        conda install pytorch torchvision cudatoolkit=10.0 -c pytorch   
