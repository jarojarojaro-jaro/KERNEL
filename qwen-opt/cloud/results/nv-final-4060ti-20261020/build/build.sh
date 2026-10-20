set -e
cd /root/src4060
for w in upstream cuda-topka2; do
  ( cmake -S $w -B $w/b89 -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89 -DGGML_CCACHE=OFF \
      -DCMAKE_CUDA_COMPILER=/home/jaro/opt/cuda-12.8/bin/nvcc -DCMAKE_CUDA_HOST_COMPILER=/usr/bin/g++ -DCUDAToolkit_ROOT=/home/jaro/opt/cuda-12.8 \
      -DCMAKE_EXE_LINKER_FLAGS=-Wl,-rpath-link,/home/jaro/opt/cuda-12.8/lib/stubs -DLLAMA_CURL=OFF > $w.cfg.log 2>&1 \
    && touch /root/bf/last-activity && cmake --build $w/b89 -j 12 --target llama-server llama-bench test-backend-ops > $w.build.log 2>&1 && echo OK > $w.rc || echo FAIL > $w.rc ) &
done
wait; touch /root/bf/last-activity; echo BUILD-DONE
