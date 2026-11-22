package judge

import "fmt"

const DemotionRevertsDone = "demotion_reverts_recorded_done"

type TaskStatusResult struct {
	Status   string   `json:"status"`
	Warnings []string `json:"warnings"`
}

func nonEmptyStr(s *string) (string, bool) {
	if s == nil || *s == "" {
		return "", false
	}
	return *s, true
}

func DetermineConservativeTaskStatus(
	requestedStatus *string,
	validationResult *string,
	operationType string,
	currentStatus *string,
	recordedValidation *string,
) (string, []string) {
	warnings := make([]string, 0)
	valid := map[string]bool{
		"planned":     true,
		"in_progress": true,
		"blocked":     true,
		"done":        true,
	}
	if req, hasReq := nonEmptyStr(requestedStatus); hasReq {
		status := req
		if !valid[status] {
			warnings = append(warnings, fmt.Sprintf("알 수 없는 상태 `%s` 는 사용할 수 없어 `planned` 로 대체한다.", status))
			status = "planned"
		}
		_, hasVal := nonEmptyStr(validationResult)
		if status == "done" && !hasVal {
			if _, hasRec := nonEmptyStr(recordedValidation); hasRec {
				warnings = append(warnings,
					"이번 호출에는 검증 결과가 없지만 task 파일에 이미 기록돼 있어 `done` 을 보존한다 (새 검증을 남기려면 `--validation-result` 를 준다).",
				)
			} else {
				status = "in_progress"
				if cur, hasCur := nonEmptyStr(currentStatus); hasCur && cur == "done" {
					warnings = append(warnings, fmt.Sprintf(
						"[%s] 검증 결과가 없어 `done` 을 `in_progress` 로 낮춘다 — 이 task 는 **이미 done 으로 기록돼 있었으므로 그 완료 기록이 취소된다** (handoff 의 최근 완료 목록 포함). 되돌릴 뜻이 아니었다면 `--validation-result` 를 주거나 `--status` 를 빼고 다시 부른다.",
						DemotionRevertsDone,
					))
				} else {
					warnings = append(warnings,
						"검증 결과가 없으므로 `done` 상태는 초안에서 `in_progress` 로 낮춘다.",
					)
				}
			}
		}
		return status, warnings
	}
	if operationType == "create_entry" {
		return "planned", warnings
	}
	if cur, hasCur := nonEmptyStr(currentStatus); hasCur && valid[cur] {
		return cur, warnings
	}
	return "in_progress", warnings
}
