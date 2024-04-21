# MPCFusion

## Welcome to follow our work: "[MPCFusion: Multiscale parallel cross-fusion for infrared and visible images via convolution and vision Transformer](https://www.sciencedirect.com/science/article/abs/pii/S0143816624000745)" 【[Paper](https://www.sciencedirect.com/science/article/abs/pii/S0143816624000745)】,【[Code](https://github.com/Haojie-Tang/MPCFusion)】.
```
@article{TANG2024MPCFusion,
title = {MPCFusion: Multi-scale parallel cross fusion for infrared and visible images via convolution and vision Transformer},
author = {Haojie Tang and Yao Qian and Mengliang Xing and Yisheng Cao and Gang Liu},
journal = {Optics and Lasers in Engineering},
volume = {176},
pages = {108094},
year = {2024},
issn = {0143-8166},
}
```

## Recommended Environment

 - [x] torch 1.11.0
 - [x] torchvision 0.12.0
 - [x] tensorboard  2.7.0
 - [x] numpy 1.21.2

## To Train
Please modify the dataset path in the train_mpcfusion.json file, and then run the following file to start training.

    python main_train_mpcfusion.py
## To Test

    python test_mpcfusion.py

## Acknowledgement
The codes are heavily based on SwinFusion. Please also follow their licenses. Thanks for their awesome works.
