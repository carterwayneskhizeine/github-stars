<h2 align="center">
  <a href="https://yuxuan-xue.com/infini-human/">InfiniHuman: Infinite 3D Human Creation with Precise Control</a>
</h2>

<h5 align="center">
  
SIGGRAPH Asia 2025, HongKong

[![arXiv](https://img.shields.io/badge/Arxiv-2510.11650-b31b1b.svg?logo=arXiv)](http://arxiv.org/abs/2510.11650) 
[![Home Page](https://img.shields.io/badge/Project-Website-C27185.svg)](https://yuxuan-xue.com/infini-human/) 

[Yuxuan Xue](https://yuxuan-xue.com/)<sup>1 </sup>, [Xianghui Xie](https://virtualhumans.mpi-inf.mpg.de/people/Xie.html)<sup>1, 2</sup>, [Margaret Kostyrko](https://yuxuan-xue.com/)<sup>1</sup>, [Gerard Pons-Moll](https://virtualhumans.mpi-inf.mpg.de/people/pons-moll.html)<sup>1, 2</sup>


<sup>1</sup>Real Virtual Human Group @ University of Tübingen & Tübingen AI Center \
<sup>2</sup>Max Planck Institute for Informatics, Saarland Informatics Campus

![](https://github.com/YuxuanSnow/InfiniHuman/blob/main/assets/teaser.gif)

## News :triangular_flag_on_post:
- [2025/10/14] InfiniHuman paper is available on [ArXiv](https://yuxuan-xue.com/infini-human).
- [2025/10/14] InfiniHumanData and InfiniHumanGen are scheduled to be released soon.

## Key Insight :raised_hands:
- Training 3D human generative models requires large-scale, diverse, and richly annotated datasets!
- Capturing and annotating real human data is prohibitively expensive and limited in scale and diversity!
- **Can we distill foundation models to generate theoretically unbounded richly annotated 3D human data?**
  - **InfiniHumanData**: Automatic pipeline distilling vision-language and image generation models => **111K diverse identities with multi-granularity annotations**
  - **Quality indistinguishable from real scans**: Users cannot tell the difference between our synthetic data and real scan renderings!
  - **InfiniHumanGen**: Diffusion-based generative model trained on InfiniHumanData => **Fast, realistic, and precisely controllable 3D human generation from text, clothing, body shape, and pose**

![](https://github.com/YuxuanSnow/InfiniHuman/blob/main/assets/pipeline_infiniHumanGen_3.png)


## Citation :writing_hand:

```bibtex
@article{xue2025infinihuman,
  author    = {Xue, Yuxuan and Xie, Xianghui and Kostyrko, Margaret and Pons-Moll, Gerard},
  title     = {InfiniHuman: Infinite 3D Human Creation with Precise Control},
  booktitle = {SIGGRAPH Asia 2025 Conference Papers},
  year      = {2025},
}
