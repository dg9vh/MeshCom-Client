# MeshCom-Client

A MeshCom-Client, written in Python, for using with MeshCom (https://icssw.org/meshcom/) Nodes

![image](https://github.com/user-attachments/assets/60b6d916-7173-42fe-9ea1-8844415e176a)

## What is this about?

This is a MeshCom-Client, that is written in Python for simple usage on a compatible computer system. Initially it is with very basic functionality but I think it will grow up over the next weeks :-)

## How to start

* Install python3 and fullfill requirements by installing all missing libraries.
* Connect your MeshCom-Node to your serial terminal and issue the following commands, to start the node to transfer data via udp to your computer:
  - --extudpip [ip of your computer]
  - --extudp on
* Go to Settings and put in the new destination ip address = ip of your node.

Now it should be running!

## Key features

* Grouping messages into tabs by destination (GRC or callsign)
* Alerting sound for new message
* Watchlist and alerting sound for callsigns in watchlist
* Restoring of chat-history on reopening chat-tabs
* Reopen specific chat on demand
* Delete complete chat history (also from restoring-source)
* Multiple languages (actually German and English)

## Functional areas

### Message area upper left

This is the place where you type your message and give the target group id or callsign. With a click on the send-button your message would be transfered via Lora to the next node and maybe to the internet server.

### Timestamp upper right

Within this box the timestamp transfered by the network every 5 minutes is shown. This is used as an indicator that the network is still alive.

### reopen previous chat upper left

As the MeshCom-Client is saving chat-history you are able to reopen chat-tabs and reload the content. With the selectbox you can select any stored chat-history and with the button you can reopen and reload the chat-history of this chat.

### chat message tabs in the lower half

This is the area where each group chat is grouped into a single tab per target. you can easily switch between the chats by selecting another tab. If there is any new message within a chat, it would be shown with a (new)-label on the tab-rider.

There are also two buttons: delete chat deletes the chat (and it's stored history) and X closes only the tab (to be reopened, if a message comes in or if you reopen it manually).

If you click on the target label, the (new)-marker would disappear in the opened tab, same if you switch over to another tab, then the label there would disappear.

### Using Watchlist

via Settings - Watchlist you can configure your personal watchlist. Here you add callsigns without SSID to be alerted with alert.wav-sound (you can replace individually to your favor).

## Easy Installation and Upgrade

Easiest way to install this is to use `pipx install MeshCom_Client`.

If you have a previous installation done with pipx you just have to use `pipx upgrade MeshCom_Client` for getting the lastest version. Maybe you have to do this more than once till it says that meshcom-client is already at latest version.

If you want to know, how to install pipx on your system, consult [GitHub - pypa/pipx: Install and Run Python Applications in Isolated Environments](https://github.com/pypa/pipx)

After installation, you can simply start the client running `MeshCom-Client` from console.

Settings-file and chat-log could be found at `.local/pipx/venvs/meshcom-client/lib/python3.11/site-packages/MeshCom_Client/` or similar.

## Troubles?

If you have issues with emojis under linux, you could try `sudo apt-get install fonts-noto*` to install needed fonts

## ToDos

* View counter of new messages in tab
* Integration in "flutter"(Android and iOS-compatibility)
* Displaying positions of stations (when receiving a pos-message) on a map (OSM)

## Contributions

Sound Effect by <a href="https://pixabay.com/de/users/freesound_community-46691455/?utm_source=link-attribution&utm_medium=referral&utm_campaign=music&utm_content=40821">freesound_community</a> from <a href="https://pixabay.com/sound-effects//?utm_source=link-attribution&utm_medium=referral&utm_campaign=music&utm_content=40821">Pixabay</a>

Sound Effect by <a href="https://pixabay.com/de/users/rescopicsound-45188866/?utm_source=link-attribution&utm_medium=referral&utm_campaign=music&utm_content=230478">Rescopic Sound</a> from <a href="https://pixabay.com/sound-effects//?utm_source=link-attribution&utm_medium=referral&utm_campaign=music&utm_content=230478">Pixabay</a>

Sound Effect by <a href="https://pixabay.com/de/users/vynadot-36505577/?utm_source=link-attribution&utm_medium=referral&utm_campaign=music&utm_content=274740">vynadot</a> from <a href="https://pixabay.com/sound-effects//?utm_source=link-attribution&utm_medium=referral&utm_campaign=music&utm_content=274740">Pixabay</a>
