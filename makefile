INDEX=index.html
PY=python.exe

all: chipinfo/$(INDEX) microshemca/$(INDEX)

chipinfo/$(INDEX): kiloom/$(INDEX)
	cd $(dir $@) && $(PY) ../chipinfo_scrap.py

kiloom/$(INDEX):
	cd $(dir $@) && $(PY) ../kiloom_scrap.py

microshemca/$(INDEX):
	cd $(dir $@) && $(PY) ../microshemca_scrap.py

clear:
	rm $(addsuffix /*.html, chipinfo kiloom microshemca)
