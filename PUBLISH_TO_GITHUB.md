# Publish to GitHub

## If you downloaded the ZIP from ChatGPT

```bash
unzip glm-localserve-ready.zip
cd glm-localserve-ready  # or the folder name created by your unzip tool
git init -b main
git add .
git commit -m "Initial GLM LocalServe implementation"
```

Then use either GitHub CLI or an existing empty repository.

### GitHub CLI

```bash
gh auth login
gh repo create glm-localserve --public --source=. --remote=origin --push
```

### Existing empty GitHub repository

```bash
git remote add origin git@github.com:YOUR_USERNAME/glm-localserve.git
git push -u origin main
```

For HTTPS instead of SSH:

```bash
git remote add origin https://github.com/YOUR_USERNAME/glm-localserve.git
git push -u origin main
```

## After the first DGX Spark run

1. Run the benchmark at concurrency 1, 4, and 8.
2. Update `BENCHMARKS.md` with measured values only.
3. Commit and push the measured results.

```bash
git add BENCHMARKS.md benchmarks/
git commit -m "Add DGX Spark GLM benchmark results"
git push
```

## Recommended repository description

> OpenAI-compatible self-hosted GLM inference service on NVIDIA DGX Spark with FastAPI, vLLM, Docker, observability, CI/CD, and reproducible benchmarks.

## Recommended topics

`llm` `vllm` `glm` `dgx-spark` `fastapi` `model-serving` `generative-ai` `inference` `benchmarking` `docker`
