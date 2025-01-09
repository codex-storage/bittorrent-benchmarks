{{/*
Expand the name of the chart.
*/}}

{{- define "filesize.bytes" }}
{{- $sizeNum := regexFind "\\d+" .Values.experiment.fileSize | int -}}
{{- $sizeUnit := regexFind "\\D+" .Values.experiment.fileSize -}}
{{- $size := dict "B" 1 "KB" 1024 "MB" 1048576 "GB" 1073741824 -}}
{{- mul $sizeNum (index $size $sizeUnit) -}}
{{- end -}}

{{- define "storage.size" }}
{{- $totalSize := mul .Values.experiment.networkSize (include "filesize.bytes" .) -}}
{{- div (mul $totalSize 12) 10 -}}
{{- end -}}

{{- define "deluge.pvc" }}
{{- default (printf "deluge-%s-pvc" (include "experiment.fullId" .)) .Values.deployment.pvcName }}
{{- end -}}

{{- define "experiment.groupId" -}}
{{- required "A valid .Values.experiment.groupId is required!" .Values.experiment.groupId }}
{{- end }}

{{- define "experiment.id"  -}}
{{- default .Release.Name .Values.experiment.id }}
{{- end }}

{{- define "experiment.fullId" -}}
{{- printf "%s-%s" (include "experiment.id" .) (include "experiment.groupId" .) }}
{{- end }}

{{/*
Common and selector labels.
*/}}
{{- define "deluge-benchmarks.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "app.name" -}}
{{- default "codex-benchmarks" .Values.deployment.appName | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "deluge-benchmarks.labels" -}}
helm.sh/chart: {{ include "deluge-benchmarks.chart" . }}
app.kubernetes.io/name: {{ include "app.name" . }}
{{ include "deluge-benchmarks.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "deluge-benchmarks.selectorLabels" -}}
app.kubernetes.io/instance: {{ include "experiment.id" . }}
app.kubernetes.io/part-of: {{ include "experiment.groupId" . }}
{{- end }}
