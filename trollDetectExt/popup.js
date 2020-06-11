var getSelectedTab = (tab) => {
  var tabId = tab.id;
  var sendMessage = (messageObj) => chrome.tabs.sendMessage(tabId, messageObj);
  document.getElementById('detect').addEventListener('click', () => sendMessage({ action: 'DETECT' }));
  document.getElementById('reset').addEventListener('click', () => sendMessage({ action: 'RESET' }))
}
chrome.tabs.getSelected(null, getSelectedTab);