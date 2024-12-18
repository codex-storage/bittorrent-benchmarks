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
{{- default (printf "deluge-%s-pvc" .Release.Name) .Values.deployment.pvcName }}
{{- end -}}

{{- define "tracker.service.name" }}
{{- printf "bittorrent-tracker-%s" .Release.Name -}}
{{- end -}}