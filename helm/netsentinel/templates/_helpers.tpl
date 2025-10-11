{{/*
Expand the name of the chart.
*/}}
{{- define "netsentinel.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "netsentinel.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "netsentinel.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "netsentinel.labels" -}}
helm.sh/chart: {{ include "netsentinel.chart" . }}
{{ include "netsentinel.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "netsentinel.selectorLabels" -}}
app.kubernetes.io/name: {{ include "netsentinel.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "netsentinel.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "netsentinel.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the proper image name
*/}}
{{- define "netsentinel.image" -}}
{{- $registryName := .Values.global.imageRegistry -}}
{{- $repositoryName := .repository -}}
{{- $tag := .tag | default .Chart.AppVersion | toString -}}
{{- if $registryName -}}
{{- printf "%s/%s:%s" $registryName $repositoryName $tag -}}
{{- else -}}
{{- printf "%s:%s" $repositoryName $tag -}}
{{- end -}}
{{- end -}}

{{/*
Return the proper image pull policy
*/}}
{{- define "netsentinel.imagePullPolicy" -}}
{{- .pullPolicy | default .Values.global.imagePullPolicy | default "IfNotPresent" -}}
{{- end -}}

{{/*
Create a default fully qualified component name.
*/}}
{{- define "netsentinel.componentName" -}}
{{- printf "%s-%s" (include "netsentinel.fullname" .) .component | trunc 63 | trimSuffix "-" -}}
{{- end -}}
