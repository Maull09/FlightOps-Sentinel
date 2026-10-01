{{- define "flightops.fullname" -}}
{{- .Release.Name -}}
{{- end -}}

{{- define "flightops.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "flightops.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
