export function completeTags(text) {
  const found = []
  const pattern = /#([^\s#]+)(?=\s)/g
  let match = pattern.exec(text || '')
  while (match) {
    if (!found.includes(match[1])) {
      found.push(match[1])
    }
    match = pattern.exec(text)
  }
  return found
}
