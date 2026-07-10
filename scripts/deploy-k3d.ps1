param(
    [string]$ReleaseName = "sly",
    [string]$Namespace = "agent-zone",
    [string]$ImageTag = "latest"
)

$ErrorActionPreference = "Stop"

helm upgrade --install $ReleaseName charts/sly `
    --namespace $Namespace `
    --create-namespace `
    --set image.tag=$ImageTag
