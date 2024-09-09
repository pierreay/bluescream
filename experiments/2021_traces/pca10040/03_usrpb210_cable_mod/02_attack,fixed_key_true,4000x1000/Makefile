# Dependencies:
# `config.mk': SHELL ; SC-COLLECT ; SC-ATTACK
# `.bashrc'  : SCHC ; SCHD ; UHD_IMAGES_DIR
include ../../../../../config.mk

# Experiment configuration.
NTRACES		= 4000
TARGET		= /dev/ttyACM0
TARGET_PWR  = 0
RADIO		= USRP_B210
ifeq ($(RADIO), USRP_B210)
	RADIOADDR = "uhd"
else ifeq ($(RADIO), HackRF)
	RADIOADDR = ""
endif

# File and folders organization.
OUT_TRACES    = collect
OUT_TEMPLATE  = template.npy
OUT_ATTACK    = attack
IN_PROFILE    = ../profile,fixed_key_false,10000x1000/profile/

.PHONY: clean backup restore

all: 4attack

# Aliases for commands below.
1init: sentinel/init
2template: $(OUT_TEMPLATE)
3collect: sentinel/collect
4attack: sentinel/attack

# Make sure that the target device and the radio are available, and prepare
# traces directory.
sentinel/init:
	mkdir -p $(@D)
	mkdir -p $(OUT_TRACES)
	file $(TARGET)
ifeq ($(RADIO), USRP_B210)
	uhd_find_devices
	uhd_find_devices
	uhd_find_devices
else ifeq ($(RADIO), HackRF)
	hackrf_info
endif
	touch $@

# Create the template. First, take a graphical quick look at the captured
# traces. Then, use the result as a template to re-create a better template.
$(OUT_TEMPLATE): sentinel/init
	$(SC-COLLECT) \
		--radio=$(RADIO) --radio-address=$(RADIOADDR) --device=$(TARGET) \
		collect 01config_template_preview.json /tmp \
		--power=$(TARGET_PWR) \
		--average-out=$(OUT_TEMPLATE) --plot \
		2> /dev/null

	$(SC-COLLECT) \
		--radio=$(RADIO) --radio-address=$(RADIOADDR) --device=$(TARGET) \
		collect 01config_template_finish.json /tmp \
		--power=$(TARGET_PWR) \
		--average-out=$(OUT_TEMPLATE) \
		2> /dev/null

# Collect the traces.
sentinel/collect: $(OUT_TEMPLATE)
	mkdir -p $(@D)
	$(SC-COLLECT) \
		--radio=$(RADIO) --radio-address=$(RADIOADDR) --device=$(TARGET) \
		collect 02config_collect.json $(OUT_TRACES) \
		2> /dev/null
	touch $@

# Attack the traces using a previously created profile.
sentinel/attack: sentinel/collect
	mkdir -p $(@D)
	$(SC-ATTACK) --norm \
		--data-path $(OUT_TRACES) --num-traces $(NTRACES) \
		--start-point 650 --end-point 800 \
		attack $(IN_PROFILE) \
		--attack-algo pcc --variable p_xor_k | tee $(OUT_ATTACK)
	touch $@

# Remove all resulting files of the experiment.
clean:
	rm -rf sentinel $(OUT_TRACES) $(OUT_TEMPLATE) $(OUT_ATTACK)

# Make a backup of the current experiment.
backup:
	mkdir backup
	[[ -e sentinel ]] && cp -r -t backup sentinel || :
	[[ -e $(OUT_TRACES) ]] && cp -r -t backup $(OUT_TRACES) || :
	[[ -e $(OUT_TEMPLATE) ]] && cp -r -t backup $(OUT_TEMPLATE) || :
	[[ -e $(OUT_ATTACK) ]] && cp -r -t backup $(OUT_ATTACK) || :

# Restore the current experiment.
restore:
	mv backup/* .
	rm -rf backup

# Display the status of the experiment.
status:
	@ [[ -a sentinel/init ]] && echo -n [OK] || echo -n [MISSING] ; echo " Initilization"
	@ [[ -a $(OUT_TEMPLATE) ]] && echo -n [OK] || echo -n [MISSING] ; echo " Template"
	@ [[ -a sentinel/collect ]] && echo -n [OK] || echo -n [MISSING] ; echo " Collect"
	@ [[ -a sentinel/attack ]] && echo -n [OK] || echo -n [MISSING] ; echo " Attack"
	@ [[ -d backup ]] && echo -n [OK] || echo -n [MISSING] ; echo " Backup"
