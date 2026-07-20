{{- define "visionone-bank-demo.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "visionone-bank-demo.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end }}

{{- define "visionone-bank-demo.labels" -}}
app.kubernetes.io/name: {{ include "visionone-bank-demo.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "visionone-bank-demo.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}{{ default (include "visionone-bank-demo.fullname" .) .Values.serviceAccount.name }}{{- else }}{{ default "default" .Values.serviceAccount.name }}{{- end }}
{{- end }}

{{- define "visionone-bank-demo.secretName" -}}
{{- if .Values.secrets.existingSecret }}{{ .Values.secrets.existingSecret }}{{- else }}{{ include "visionone-bank-demo.fullname" . }}{{- end }}
{{- end }}
