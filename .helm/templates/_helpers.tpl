{{- define "foodgram.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "foodgram.fullname" -}}
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

{{- define "foodgram.labels" -}}
app.kubernetes.io/name: {{ include "foodgram.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Resolve the backend image.
Priority: 1) werf-injected .Values.werf.image.backend
           2) global.image.backend (set by CI --set)
           3) backend.image.registry/repository:tag
*/}}
{{- define "foodgram.backendImage" -}}
{{- if .Values.werf }}
{{- index .Values.werf.image "backend" }}
{{- else if .Values.global.image.backend }}
{{- .Values.global.image.backend }}
{{- else if .Values.backend.image.registry }}
{{- printf "%s/%s:%s" .Values.backend.image.registry .Values.backend.image.repository .Values.backend.image.tag }}
{{- else }}
{{- printf "%s:%s" .Values.backend.image.repository .Values.backend.image.tag }}
{{- end }}
{{- end }}

{{/*
Resolve the frontend image.
Priority: 1) werf-injected .Values.werf.image.frontend
           2) global.image.frontend (set by CI --set)
           3) frontend.image.registry/repository:tag
*/}}
{{- define "foodgram.frontendImage" -}}
{{- if .Values.werf }}
{{- index .Values.werf.image "frontend" }}
{{- else if .Values.global.image.frontend }}
{{- .Values.global.image.frontend }}
{{- else if .Values.frontend.image.registry }}
{{- printf "%s/%s:%s" .Values.frontend.image.registry .Values.frontend.image.repository .Values.frontend.image.tag }}
{{- else }}
{{- printf "%s:%s" .Values.frontend.image.repository .Values.frontend.image.tag }}
{{- end }}
{{- end }}
