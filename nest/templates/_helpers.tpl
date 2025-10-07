{{/*
Expand the name of the chart.
*/}}
{{- define "algoitny-backend.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "algoitny-backend.fullname" -}}
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
{{- define "algoitny-backend.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "algoitny-backend.labels" -}}
helm.sh/chart: {{ include "algoitny-backend.chart" . }}
{{ include "algoitny-backend.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "algoitny-backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "algoitny-backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "algoitny-backend.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "algoitny-backend.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Gunicorn labels
*/}}
{{- define "algoitny-backend.gunicorn.labels" -}}
{{ include "algoitny-backend.labels" . }}
app.kubernetes.io/component: gunicorn
{{- end }}

{{/*
Celery Worker labels
*/}}
{{- define "algoitny-backend.celeryWorker.labels" -}}
{{ include "algoitny-backend.labels" . }}
app.kubernetes.io/component: celery-worker
{{- end }}

{{/*
Celery Beat labels
*/}}
{{- define "algoitny-backend.celeryBeat.labels" -}}
{{ include "algoitny-backend.labels" . }}
app.kubernetes.io/component: celery-beat
{{- end }}
