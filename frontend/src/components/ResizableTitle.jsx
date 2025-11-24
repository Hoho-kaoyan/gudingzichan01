import React from 'react'
import { Resizable } from 'react-resizable'
import 'react-resizable/css/styles.css'

const ResizableTitle = (props) => {
  const { onResize, width, ...restProps } = props

  // 如果没有宽度或没有onResize回调，直接渲染普通th
  if (!width || !onResize) {
    return <th {...restProps} />
  }

  return (
    <Resizable
      width={width}
      height={0}
      handle={
        <span
          className="react-resizable-handle"
          onClick={(e) => e.stopPropagation()}
        />
      }
      onResize={onResize}
      draggableOpts={{ enableUserSelectHack: false }}
    >
      <th {...restProps} />
    </Resizable>
  )
}

export default ResizableTitle



