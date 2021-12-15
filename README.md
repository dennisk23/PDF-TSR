# Table structure recognition in academic papers

This project is built upon an earlier project by Rink Stiekema https://github.com/rinkstiekema/PDF-Table-Structure-Recognition-using-deep-learning. It contains a pipeline that takes a folder of PDF files (academic papers) as input and outputs CSV files of tables.

## Getting Started

Install the requirements found in requirements.txt using `conda create --name <env> --file requirements.txt` (python 3)

You can generate a dataset using `/tablegenerator/tablegen.py` and `/tablegenerator/tablegen_special.py`. See the README file in the tablegenerator folder for more information on this process.

Running the pipeline requires a pretrained model. Two pretrained models are available, namely pix2pixHD and SegNet. Their checkpoints are stored in the `models` directory.
The pix2pixHD model is based on NVIDIA's https://github.com/NVIDIA/pix2pixHD/.
The SegNet model is based on https://github.com/GeorgeSeif/Semantic-Segmentation-Suite. (Encoder-Decoder with skipconnections, InceptionV4)

## Running the pipeline

You can run the pipeline using `python ./pipeline/batch.py`. Following options are available:

* --dataroot, folder of PDF files
* --model, options: 'pix2pixHD' and 'encoder-decoder-skip'
* --checkpoint_dir, required for pix2pixHD only
* --skip_generate_images, skips the extraction of tables using pdffigures2
* --skip_pad_images, skips the padding of images to make them 1024x1024 pixels
* --skip_predict, skips the prediction phase
* --skip_find_cells, skips finding the cells based on the outlines
* --skip_extract_text, skips extracting the text from the cells using Fitz
* --skip_create_csv, skips the creation of a csv based on the found text and cells

### Installing

`conda create --name <env> --file requirements.txt`

For the usage of the pix2pixHD model, the installation of apex is required https://github.com/NVIDIA/apex

## Test dataset

Three test datasets are available on Google Drive. It contains non-academic tables from the ICDAR 2013 table competition, academic tables from the AAAI 2018 conference, and academic tables from nine conferences over the years 2014 to 2019.
https://drive.google.com/drive/folders/1n_FDbN3P3FWARaOSpHpWj_pN9YizlAcu?usp=sharing

## Acknowledgments

* NVIDIA's pix2pixHD
* George Seif's Semantic-Segmentation-Suite
* Allen AI's Pdffigures2
* PyMuPDF's Fitz
