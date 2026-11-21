# Content Agents v2 (free + local)

Topics ki list do -> har topic ke liye: Research (concepts + history) -> Outline -> Storyteller -> PDF -> PPT -> Reviewer.
Reviewer flaw dekhe to purane agents ko khud dobara chalata hai. Koi paid API nahi, sab Ollama par local.

## Setup (ek baar)
1. Ollama install karo, phir `ollama pull qwen2.5:7b-instruct`
2. `pip install -r requirements.txt`

## Chalana
- Web UI: `streamlit run app.py`  (list paste karo, Start dabao, 4-5 ghante chalne do)
- Terminal: `python main.py --file topics.txt --language Hinglish --mentor "Naam"`

## Output
`output/<playlist_naam>/01_topic/` ke andar: PDF, PPTX, research/outline/story .md, review.json.
Browser se folder download nahi hota, isliye files PC par is folder mein pehle se save hoti rehti hain.
UI mein: har done topic ke saamne PDF / PPT / ZIP button (batch chalte waqt bhi), aur "ALL ZIP" button.

## Resume
Beech mein ruk jaye (power cut, Stop) to same playlist naam ke saath wahi list dobara Start karo.
Jo topics ban chuke hain wo skip ho jaate hain.

## Notes
- History ke liye research alag se hoti hai (kisne banaya, kya problem thi, limitations, better approach).
  Model ko naam/date invent karne se roka gaya hai; sources mein na mile to "not clearly documented" likhta hai.
- PDF mein Devanagari font nahi hai, isliye Hinglish Roman script mein hai.
"# Notes-PPT-Agent" 
