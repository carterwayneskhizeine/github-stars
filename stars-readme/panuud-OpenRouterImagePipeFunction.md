In the current latest version, chatting directly with image models *seems* to be supported — but you’ll likely need to set:  
```env
CHAT_STREAM_RESPONSE_CHUNK_MAX_BUFFER_SIZE=20971520
```
(this should handle ~20 MB images)
in your environment for image responses to stream properly.  

<br>
<br>
<br>
<br>
<br>

### (Older Versions)  
↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓

**This pipe integrates OpenRouter’s image-capable models (like `google/gemini-2.5-flash-image`) into OpenWebUI.**

⚠️ **Important**: When using this pipe, set an *External Task Model* in OpenWebUI settings.  
This pipe triggers on system tasks (tags, title, etc.). If those tasks also call this pipe, it can cause errors at the end — even if image generation/editing works fine.

get function: https://openwebui.com/f/panuud/openrouterimage
