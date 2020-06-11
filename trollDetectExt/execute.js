const rotateEvent = (deg) => {
  document.body.style.transform = 'rotate('+deg+'deg)';
};
const reset = () => {
  document.body.style.transform = '';
}
const displayTroll = (list) =>{
  var trollList = [];
  for (i = 0; i < list.length; i++){
    if(list[i] == "0" || list[i] == "1"){
      trollList.push(list[i]);
    }
  }
  console.log(trollList);
  for (j = 0; j < trollList.length; j++){
    if(trollList[j] == "1"){
      document.getElementsByClassName("comment-content")[0].children[j].style.filter="blur(5px)";
    }
  }
}

const onMessage = (message) => {
  switch (message.action) {
    case 'DETECT':
      rotateEvent(90);
      break;
    case 'RESET':
      reset();
      break;
    default:
      break;
  }
}

chrome.runtime.onMessage.addListener(onMessage);

window.addEventListener("message", function(e)
{
  console.log(e.data);
  chrome.runtime.sendMessage(e.data, (response) => {
        //console.log(response);
        displayTroll(response);

  });
}, false);