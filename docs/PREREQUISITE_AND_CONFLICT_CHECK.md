# Pre-check Requirement dan Potensi Konflik

Urutan ini sengaja dimulai dari **existing cluster inventory**. Tidak ada resource yang boleh dibuat sebelum kita mengetahui aplikasi, hostname, release, policy, storage, dan resource lain yang sudah ada di cluster.

## 1. Inventory existing applications di Kubernetes — read-only

Set target yang direncanakan, tetapi jangan membuat namespace atau resource apa pun:

```bash
export NAMESPACE=visionone-demo
export RELEASE=visionone-bank-demo
export HOST=ai-bank.trend-id.top
export INGRESS_CLASS=nginx
export TLS_SECRET=ai-bank-trend-id-tls
export SECRET_NAME=visionone-bank-demo-secrets

./scripts/cluster-inventory.sh
```

Script ini hanya menjalankan operasi baca (`get`, `list`, dan metadata inspection). Hasil lengkap disimpan ke:

```text
/tmp/visionone-bank-demo-cluster-inventory-<timestamp>.txt
```

Yang diperiksa:

- kubeconfig context dan API server yang sedang aktif;
- seluruh Deployment, StatefulSet, DaemonSet, Service, dan Ingress;
- Helm releases yang sudah ada;
- resource di target namespace;
- benturan nama Deployment, Service, ConfigMap, PVC, Ingress, ServiceAccount, HPA, dan NetworkPolicy;
- benturan hostname Ingress;
- Secret aplikasi dan TLS Secret yang sudah ada;
- Pod Security Admission, ResourceQuota, LimitRange, dan NetworkPolicy;
- StorageClass dan PVC existing;
- policy engine seperti Kyverno atau Gatekeeper;
- service AI Guard, LiteLLM, LLM, model, atau inference yang mungkin sudah tersedia;
- kapasitas dan utilization node bila Metrics Server tersedia.

Keputusan:

```text
Decision: STOP
```

berarti ada konflik yang harus diselesaikan. Jangan lanjut.

```text
Decision: INVENTORY CLEAR WITH ... WARNING(S)
```

berarti tidak ada konflik fatal, tetapi seluruh warning tetap harus direview.

### Verifikasi context secara manual

```bash
kubectl config current-context
kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}{"\n"}'
kubectl get nodes -o wide
```

Pastikan ini benar-benar cluster demo/lab yang dituju, bukan cluster produksi.

## 2. Putuskan placement dan identitas deployment

Setelah inventory, tentukan parameter final yang tidak berbenturan:

```bash
export NAMESPACE=visionone-demo
export RELEASE=visionone-bank-demo
export HOST=ai-bank.trend-id.top
export INGRESS_CLASS=nginx
export TLS_SECRET=ai-bank-trend-id-tls
export SECRET_NAME=visionone-bank-demo-secrets
export TMV1_REGION=sg
export FILE_SECURITY_REGION=ap-southeast-1
```

Rekomendasi:

- gunakan namespace khusus;
- gunakan hostname khusus yang belum dipakai;
- pertahankan release name unik;
- jangan memakai Secret/PVC existing yang tidak jelas ownership-nya;
- jangan memasang aplikasi ini ke namespace aplikasi customer lain.

Chart sekarang membentuk nama resource dari Helm release secara standar. Release dengan nama berbeda tidak lagi otomatis menghasilkan Deployment/Service/PVC dengan nama yang sama.

## 3. Jalankan requirement preflight

### 3.1 Workstation/build preflight

```bash
./scripts/preflight-check.sh --local-only
```

Memeriksa Bash, cURL, OpenSSL, Python, Docker/Podman, Helm, kubectl, TMAS, jq, file project, Helm lint, EICAR build context, dan kompatibilitas RWO dengan replica/HPA.

### 3.2 Cluster preflight

```bash
./scripts/preflight-check.sh --cluster-only
```

Memeriksa API access, RBAC, IngressClass, hostname, Helm release, Secret, TLS, StorageClass, HPA metrics, Pod Security, dan NetworkPolicy.

### 3.3 Active network dan image-pull test

Tahap ini membuat pod sementara, sehingga hanya dijalankan **setelah Step 1 inventory dinyatakan clear**:

```bash
APP_IMAGE=registry.example.com/security/visionone-bank-demo:1.0.0 \
./scripts/preflight-check.sh --cluster-only --active-network
```

Hasil akhir harus `FAIL=0`. Warning harus diterima secara sadar sebelum deployment.

## 4. Requirement minimum

### Workstation

- Bash, cURL, OpenSSL, Python 3.
- Docker atau Podman yang dapat mengakses daemon.
- Helm 3.
- `kubectl` dengan context cluster yang benar.
- TMAS CLI untuk live AI Scanner.
- `jq` direkomendasikan untuk membaca JSON.

### Kubernetes

- Kubernetes API dapat diakses.
- Hak RBAC untuk Deployment, Service, ConfigMap, Secret, ServiceAccount, PVC, Ingress, NetworkPolicy, dan HPA.
- Ingress Controller berjalan dan `IngressClass` sesuai values.
- Default StorageClass tersedia, atau `persistence.storageClass` diisi.
- DNS cluster bekerja.
- Worker node dapat menarik image dari registry.
- Resource minimum awal: request 100m CPU/256Mi dan limit 1 CPU/1Gi untuk satu pod.

### Trend Vision One

- Entitlement/trial AI Application Security dan File Security aktif.
- AI Guard configuration dibuat dan diterapkan.
- API key AI Guard memiliki permission yang diminta tenant untuk detection API.
- API key AI Scanner memiliki seluruh permission yang diperlukan TMAS.
- API key File Security memiliki permission `Run file scan via SDK`.
- API key dan endpoint region harus sesuai tenant.

## 5. Konflik Kubernetes yang harus dinilai

### 5.1 Existing resource dengan nama sama

Resource dengan nama yang sama dapat diadopsi/ditolak oleh Helm atau menimpa ekspektasi aplikasi. Inventory script memeriksa:

```text
Deployment
Service
ConfigMap
PersistentVolumeClaim
Ingress
ServiceAccount
HorizontalPodAutoscaler
NetworkPolicy
```

Resource existing hanya aman bila metadata menunjukkan resource tersebut memang dimiliki Helm release yang sama dan deployment yang dilakukan adalah upgrade terencana.

### 5.2 Ingress hostname

Pemeriksaan manual:

```bash
kubectl get ingress -A \
  -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{range .spec.rules[*]}{.host}{" "}{end}{"\n"}{end}' \
  | grep -w ai-bank.trend-id.top
```

Hostname yang sama pada Ingress lain dapat mengarahkan traffic ke backend yang salah atau ditolak controller.

### 5.3 Ingress controller

Values contoh memakai `nginx`. Bila cluster memakai ALB, Traefik, HAProxy, OpenShift Route, atau controller lain:

- ubah `ingress.className`;
- hapus/ganti annotation `nginx.ingress.kubernetes.io/*`;
- sesuaikan TLS, timeout, dan upload size.

### 5.4 PVC versus replica/HPA

Default PVC adalah `ReadWriteOnce`. Konfigurasi aman:

```yaml
replicaCount: 1
autoscaling:
  enabled: false
persistence:
  enabled: true
  accessModes: ["ReadWriteOnce"]
```

Chart menolak RWO bila multi-replica atau HPA lebih dari satu pod. Untuk scale-out, gunakan RWX, object storage, atau state eksternal.

### 5.5 ResourceQuota, LimitRange, dan Pod Security

```bash
kubectl -n "$NAMESPACE" get resourcequota
kubectl -n "$NAMESPACE" get limitrange
kubectl get ns "$NAMESPACE" --show-labels
```

Chart menggunakan non-root user, read-only root filesystem, drop all capabilities, dan RuntimeDefault seccomp. Meski demikian, admission policy custom tetap dapat menolak image registry, required labels, resource limits, volume type, atau Ingress annotation.

### 5.6 Existing NetworkPolicy

```bash
kubectl -n "$NAMESPACE" get networkpolicy -o yaml
```

Default-deny existing dapat memblok:

- ingress dari Ingress Controller;
- DNS ke CoreDNS;
- HTTPS ke Trend Vision One;
- gRPC/TLS ke File Security;
- private LLM atau proxy internal.

## 6. Network, proxy, dan certificate

### Trend-hosted AI Guard

Pod membutuhkan DNS dan HTTPS/TCP 443 ke endpoint regional, misalnya tenant Singapore:

```text
api.sg.xdr.trendmicro.com:443
```

### File Security SDK

Untuk `ap-southeast-1`, SDK menggunakan gRPC/TLS port 443. Pastikan proxy/firewall mendukung HTTP/2 dan tidak memutus koneksi gRPC:

```text
antimalware.ap-southeast-1.cloudone.trendmicro.com:443
```

### Corporate proxy

```yaml
extraEnv:
  - name: HTTPS_PROXY
    value: http://proxy.example.com:8080
  - name: HTTP_PROXY
    value: http://proxy.example.com:8080
  - name: NO_PROXY
    value: .svc,.cluster.local,127.0.0.1,localhost
```

### Private CA

Jika corporate TLS inspection digunakan, mount corporate CA dan set `SSL_CERT_FILE` hanya bila kebijakan organisasi memerlukannya.


## 7. DNS dan TLS

```bash
nslookup "$HOST"
kubectl get ingress -n "$NAMESPACE"
openssl s_client -connect "$HOST:443" -servername "$HOST" </dev/null
```

Periksa:

- TLS Secret ada dan bertipe `kubernetes.io/tls`;
- certificate SAN memuat hostname;
- DNS menunjuk load balancer yang benar;
- WAF mengizinkan POST dan multipart upload;
- body-size lebih besar dari `MAX_UPLOAD_MB` plus multipart overhead;
- reverse proxy tidak menghapus header `Authorization`.

## 8. Image dan EICAR

EICAR tidak disimpan di container image. Buat hanya pada mesin demo terkontrol:

```bash
./scripts/create-eicar-sample.sh /tmp/eicar.com.txt
```

Jangan mengirim EICAR melalui email atau chat corporate.

## 9. AI Scanner reachability

AI Scanner mendukung target REST API publik maupun privat. Pastikan endpoint berikut dapat dicapai dari jalur eksekusi TMAS yang digunakan:

```text
https://ai-bank.trend-id.top/api/ai/vulnerable/v1/chat/completions
https://ai-bank.trend-id.top/api/ai/protected/v1/chat/completions
```

Keduanya OpenAI-compatible, sehingga target type yang dipilih adalah **Model Endpoint (OpenAI-compliant)**. Untuk endpoint privat di lab, jalankan TMAS dari host yang memiliki route ke NodePort/Ingress privat. Untuk endpoint publik, gunakan HTTPS dan sertifikat valid.

## 10. File Security Storage — optional

Storage mode memerlukan bucket yang sudah dimonitor, `s3:PutObject`, region yang benar, dan workload identity/IRSA yang sesuai.

## 11. Go/no-go sebelum demo

```text
[ ] cluster-inventory.sh selesai tanpa FAIL
[ ] kubeconfig context sudah dikonfirmasi
[ ] tidak ada exact resource-name collision
[ ] tidak ada Ingress hostname collision
[ ] existing Secret/PVC sudah diverifikasi ownership-nya
[ ] ResourceQuota/LimitRange/Pod Security kompatibel
[ ] existing NetworkPolicy sudah dianalisis
[ ] preflight local FAIL=0
[ ] preflight cluster FAIL=0
[ ] active network dan image-pull test lulus
[ ] /api/preflight ready=true
[ ] AI Guard live, bukan fallback
[ ] File Security live, bukan fallback
```
