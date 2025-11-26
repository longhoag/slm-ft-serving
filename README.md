# slm-ft-serving

I have done a project that fine tunes the llama 3.1 8B model using 4-bit quantization qLoRA technique for medical cancer-specific information extraction (IE) on EC2 instance. Then I pushed the adapter after fine-tuning to my model repo on Hugging Face which consists of these files: .gitattributes, README.md, adapter_config.json, adapter_model.safetensors, special_tokens_map.json, tokenizer.json, tokenizer_config.json, training_args.bin

This project is to serve that fine-tuned llama 3.1 8B model using vLLM with a focus of optmization technique with vLLM.

To let you better understand the fine-tuned model, I trained with the synthetic data with one entry of the training data as follows:  {"instruction": "Extract all cancer-related entities from the text.", "input": "70-year-old man with widely metastatic cutaneous melanoma. PD-L1 was 5% on IHC and NGS reported TMB-high; BRAF testing was not performed prior to treatment. Given multiple symptomatic brain metastases he received combination immunotherapy with nivolumab plus ipilimumab and stereotactic radiosurgery to dominant intracranial lesions. Imaging after two cycles demonstrated some shrinking of index lesions but appearance of a new small lesion \u2014 overall assessment called a mixed response.", "output": {"cancer_type": "melanoma (cutaneous)", "stage": "IV", "gene_mutation": null, "biomarker": "PD-L1 5%; TMB-high", "treatment": "nivolumab and ipilimumab; stereotactic radiosurgery", "response": "mixed response", "metastasis_site": "brain"}}

My current planning of this project will be split into 4 different stages. We need to complete each stage first then move to the next. One stage requires a different repo for better organization of frontend and backend.  I just plan ahead so that you can get a better picture of the project, avoiding unorganized architecture when we build more layer into the system. 

Stage 1: Deploy EC2 instance for the vLLM server.
- The choice of the instance is g6.2xlarge (us-east-1)
- EBS root volume of 50 Gib or 100 Gib (suggest a storage size: efficient and cost-saving?)

Planned CI/CD pipeline for stage 1:
- Github actions (fully automated): build docker image and push to ECR
- Setup scripts (execute from local terminal): 
1. Start EC2 instance
1.1 Wait for status ok
2. Send SSM run command to deploy

Note on serving model in this stage: The base model is on Hugging Face with this path: meta-llama/Llama-3.1-8B; and my fine-tuned adapter is under my repo with path: loghoag/llama-3.1-8b-medical-ie; So that you know when loading the model we would have to load the base model and the adapters I trained.

Stage 2: Add lightweight Backend Gateway FastAPI
Planned CI/CD pipeline for stage 2:
- Github actions build 2 docker images and push to ECR (vLLM + API gateway)
- Deploy on EC2 from SSM run command sent from local like we did in stage 1

+ Dependencies: API gateway waits until vLLM is healthy 
We can add tests: 
- linting
- API tests
- vLLM connectivity test

Note: We add this layer on the same EC2 instance as vLLM server.

Stage 3: Add front end using React + Next.js on Vercel. We will have this front end on a seperate git repo, but you would get the idea that we would want to have an UI for this model serving.

Route53 DNS --> AWS ALB --> EC2 instance 

Planned CI/CD pipeline:
- Push front end --> Vercel auto builds and deploys

Stage 4: Add monitoring and observability to monitor LLM inference
We can add: 
- CloudWatch GPU metrics
- Logs for vLLM container
- Dashboarding  


Project Overall Note: 
- I would like to send command from the local terminal and run everything remotely on EC2 via AWS SSM (no need to connect to EC2 instance via SSH or the need of .pem key). With a lot of setup and moving parts, I would want the command to be execute with precaution to errors, enable failsafe measures, etc.
- With different stages, the file architecture can add up, but when implementing the stage 1, don't create the architecture for stage 2 or 4. We will gradually add them up so that we can make sure there are no errors or disorganization downstream. 

- Keys need to be set up (there may be more than this, please suggest all the keys needed for set up but for follow in each stage): 
+ HF access token: to retrieve llama model
+ AWS access key + secret access key 
+ ECR

Requirements:
- use AWS secrets manager to store keys, access tokens, etc. then use SSM parameter store to reference the key --> SSM and secrets manager integration for ease-of-use and privacy. Not using regular .env file because we would run command remotely on EC2 instance
- Use CloudWatch to log output and session from SSM run command
- use poetry for dependencies management (if needed for local script execution)
- use loguru logger instead of printing statements (if needed for local script execution)