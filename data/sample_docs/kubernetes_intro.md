# Kubernetes Introduction

Kubernetes (K8s) is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications. Originally developed by Google, it's now maintained by the Cloud Native Computing Foundation (CNCF).

## Why Kubernetes?

Running containers in production requires:
- Automatic scaling based on demand
- Load balancing across multiple instances
- Self-healing when containers fail
- Rolling updates without downtime
- Service discovery and networking
- Secret and configuration management

Kubernetes provides all of these capabilities out of the box.

## Core Concepts

### Pods

A Pod is the smallest deployable unit in Kubernetes. It represents a single instance of a running process and can contain one or more containers.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
  - name: app
    image: myapp:1.0
    ports:
    - containerPort: 8080
```

Pods are ephemeral - they can be created and destroyed at any time. Don't create Pods directly; use higher-level abstractions like Deployments.

### Deployments

Deployments manage the desired state of Pods and ReplicaSets. They handle:
- Scaling (running multiple replicas)
- Rolling updates
- Rollbacks
- Self-healing

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: myapp:1.0
        ports:
        - containerPort: 8080
```

### Services

Services provide stable networking for Pods. Since Pods are ephemeral and can have changing IP addresses, Services provide a consistent endpoint.

**ClusterIP** (default): Internal cluster communication only
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app-service
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

**NodePort**: Exposes service on each Node's IP at a static port
```yaml
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 8080
    nodePort: 30080
```

**LoadBalancer**: Creates an external load balancer (cloud providers)
```yaml
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
```

### Namespaces

Namespaces provide logical isolation within a cluster. They're useful for:
- Organizing resources
- Multi-tenancy
- Resource quotas
- Access control

```bash
# Create namespace
kubectl create namespace production

# List namespaces
kubectl get namespaces

# Use specific namespace
kubectl get pods -n production
```

Common namespaces:
- `default`: Default namespace for resources
- `kube-system`: Kubernetes system components
- `kube-public`: Publicly accessible resources
- `kube-node-lease`: Node heartbeat data

### ConfigMaps

ConfigMaps store non-sensitive configuration data as key-value pairs.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  database_url: "postgresql://db:5432/myapp"
  log_level: "INFO"
  max_connections: "100"
```

Use in a Pod:
```yaml
spec:
  containers:
  - name: app
    env:
    - name: DATABASE_URL
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: database_url
```

### Secrets

Secrets store sensitive data like passwords, tokens, and keys. They're base64 encoded (not encrypted by default).

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=  # base64 encoded
  api-key: bXktYXBpLWtleQ==
```

Use in a Pod:
```yaml
spec:
  containers:
  - name: app
    env:
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: app-secrets
          key: password
```

### Volumes

Volumes provide persistent storage for Pods.

**EmptyDir**: Temporary storage, deleted when Pod terminates
```yaml
volumes:
- name: cache
  emptyDir: {}
```

**HostPath**: Mounts directory from host node
```yaml
volumes:
- name: data
  hostPath:
    path: /mnt/data
    type: Directory
```

**PersistentVolume & PersistentVolumeClaim**: Persistent storage abstraction
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

## kubectl Commands

### Cluster Information

```bash
# Get cluster info
kubectl cluster-info

# View nodes
kubectl get nodes

# Detailed node info
kubectl describe node node-name
```

### Working with Pods

```bash
# List pods
kubectl get pods

# Pod details
kubectl describe pod my-pod

# Pod logs
kubectl logs my-pod

# Follow logs
kubectl logs -f my-pod

# Execute command in pod
kubectl exec -it my-pod -- /bin/bash

# Delete pod
kubectl delete pod my-pod
```

### Working with Deployments

```bash
# Create deployment
kubectl create deployment my-app --image=myapp:1.0

# List deployments
kubectl get deployments

# Scale deployment
kubectl scale deployment my-app --replicas=5

# Update image
kubectl set image deployment/my-app app=myapp:2.0

# View rollout status
kubectl rollout status deployment/my-app

# Rollback to previous version
kubectl rollout undo deployment/my-app

# View rollout history
kubectl rollout history deployment/my-app
```

### Working with Services

```bash
# List services
kubectl get services

# Service details
kubectl describe service my-service

# Delete service
kubectl delete service my-service
```

### Apply Configuration

```bash
# Apply from file
kubectl apply -f deployment.yaml

# Apply directory
kubectl apply -f ./configs/

# Delete from file
kubectl delete -f deployment.yaml
```

## Labels and Selectors

Labels are key-value pairs attached to objects for organization and selection.

```yaml
metadata:
  labels:
    app: my-app
    environment: production
    version: "1.0"
```

Selectors find objects with specific labels:
```bash
# Get pods with specific label
kubectl get pods -l app=my-app

# Get pods with multiple labels
kubectl get pods -l app=my-app,environment=production
```

## Health Checks

### Liveness Probe

Checks if container is alive. Kubelet restarts container if probe fails.

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Readiness Probe

Checks if container is ready to receive traffic. Service removes Pod from endpoints if probe fails.

```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Startup Probe

Checks if application has started. Used for slow-starting containers.

```yaml
startupProbe:
  httpGet:
    path: /startup
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
```

## Resource Management

### Resource Requests and Limits

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "500m"
  limits:
    memory: "512Mi"
    cpu: "1000m"
```

- **Requests**: Minimum resources guaranteed
- **Limits**: Maximum resources allowed

### Horizontal Pod Autoscaler

Automatically scales Pods based on metrics:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

## Architecture

### Control Plane Components

- **API Server**: Frontend for Kubernetes control plane
- **etcd**: Key-value store for cluster data
- **Scheduler**: Assigns Pods to Nodes
- **Controller Manager**: Runs controller processes
- **Cloud Controller Manager**: Cloud-specific control logic

### Node Components

- **kubelet**: Agent that ensures containers are running
- **kube-proxy**: Network proxy maintaining network rules
- **Container Runtime**: Runs containers (Docker, containerd, CRI-O)

Kubernetes provides a powerful platform for container orchestration, enabling teams to deploy and manage applications at scale with reliability and efficiency.
