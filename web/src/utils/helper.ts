//与UI无关的函数

// 不用navigator.clipboard.writeText的原因：该接口需要在HTTPS环境下才能使用
export function copyText(text: string) {
  let inputDom = document.createElement('input');
  inputDom.setAttribute('type', 'text');
  inputDom.value = text;
  //需要将元素添加到文档中去才可以跟文档结构中的其他元素交互
  document.body.appendChild(inputDom);
  inputDom.select();
  //返回false则浏览器不支持该api
  let res = document.execCommand('copy');
  document.body.removeChild(inputDom)
  return res
}
export function getTailPath(){
  return location.hash.split('/').pop()?.split('?')[0]
}
