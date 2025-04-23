#!/bin/bash
function record_process() {
    ./06_record.sh >/dev/null 2>&1
    ./07_post-process.sh | grep position
}
i=0; while (( $i < 50 )); do record_process && let i++; done
