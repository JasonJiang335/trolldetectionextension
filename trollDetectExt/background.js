chrome.runtime.onInstalled.addListener(function(){
	chrome.declarativeContent.onPageChanged.removeRules(undefined, function(){
		chrome.declarativeContent.onPageChanged.addRules([
			{
				conditions: [
					new chrome.declarativeContent.PageStateMatcher({pageUrl: {urlContains: 'm.weibo.cn'}})
				],
				actions: [new chrome.declarativeContent.ShowPageAction()]
			}
		]);
	});
});

function fetchCorsData(url, callback) {
  const commentRequest = new XMLHttpRequest();
  const reqURL = 'http://127.0.0.1:5000/detection';
  
  commentRequest.onreadystatechange = function() {//Call a function when the state changes.
      if(commentRequest.readyState == 4 && commentRequest.status == 200) {
        	//console.log(commentRequest.responseText);
        	callback(commentRequest.responseText);
      }
  }
  commentRequest.open("POST", reqURL, true);
  let reqData = new FormData();
  reqData.append('', url);
  commentRequest.send(reqData);
};

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
	console.log(message.url);
    if (!message.url) {
        return null;
    } else {
        fetchCorsData(message.url, (result) => {
        	//console.log(result);
            sendResponse(result);
        });
        return true;
    }
});