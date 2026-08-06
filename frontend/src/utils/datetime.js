/**
 * 时间格式化公共工具
 * 强制按东八区(Asia/Shanghai)显示，避免海外/不同时区浏览器显示漂移
 */

/**
 * 将 ISO 字符串（或后端返回的 +08:00 字符串）按东八区格式化为本地字符串
 * @param {string|null|undefined} iso
 * @param {string} [withSec=false] 是否显示秒
 * @returns {string} 格式化结果；空值返回 '-'
 */
export const formatEast8 = (iso, withSec = false) => {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  const options = {
    timeZone: 'Asia/Shanghai',
    hour12: false,
  }
  if (withSec) {
    return d.toLocaleString('zh-CN', { ...options, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }
  return d.toLocaleString('zh-CN', options)
}

/**
 * 仅日期（YYYY/MM/DD），按东八区
 */
export const formatEast8Date = (iso) => {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  return d.toLocaleDateString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

/**
 * 仅时间（HH:mm:ss），按东八区
 */
export const formatEast8Time = (iso) => {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  return d.toLocaleTimeString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}