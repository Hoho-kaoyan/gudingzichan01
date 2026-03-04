/**
 * 联动安全检查相关 400 错误解析与展示（角色 D：业务提示与引导）
 * 当交接/退回/调拨等接口因「需先完成数据安全检查」返回 400 时，前端统一解析并引导至「我的检查任务」。
 */

/** 后端可能返回的「需先完成数据安全检查」类文案（含部分匹配） */
const SAFETY_CHECK_KEYWORDS = ['数据安全检查', '完成数据安全', '请先由当前所有人完成', '请先完成']

/**
 * 从接口错误响应中解析出 detail 文案
 * @param {object} error - axios 错误对象，error.response?.data 可能为 { detail: string } 或 { detail: string[] } 或 { message: string }
 * @returns {string} 解析出的错误文案
 */
export function getDetailMessage(error) {
  if (!error?.response?.data) return ''
  const data = error.response.data
  const detail = data.detail ?? data.message
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) return detail[0]
  return ''
}

/**
 * 判断是否为「需先完成数据安全检查」类 400 错误
 * @param {object} error - axios 错误对象
 * @returns {{ isSafetyCheck: boolean, message: string }}
 */
export function parseSafetyCheckError(error) {
  const status = error?.response?.status
  const message = getDetailMessage(error)
  const isSafetyCheck =
    status === 400 &&
    SAFETY_CHECK_KEYWORDS.some((kw) => message && message.includes(kw))
  return { isSafetyCheck, message: message || '操作失败，请稍后重试' }
}
