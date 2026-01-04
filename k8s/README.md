# Kubernetes Manifests (Optional)

These manifests are reference examples and may need adaptation for your cluster
(storage class, ingress controller, secrets management).

Resources:
- postgres Deployment + Service (demo only; prefer StatefulSet in real setups)
- backend Deployment + Service
- frontend Deployment + Service
- nginx Deployment + Service + Ingress

Apply:

```bash
kubectl apply -f k8s/
```
