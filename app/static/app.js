document.addEventListener('DOMContentLoaded', () => {
	const btn = document.getElementById('captureBtn');
	const statusEl = document.getElementById('status');
	if (btn) {
		btn.addEventListener('click', async () => {
			statusEl.textContent = 'Capturing...';
			btn.disabled = true;
			try {
				const res = await fetch('/api/capture_detect', { method: 'POST' });
				if (!res.ok) throw new Error('Request failed');
				const data = await res.json();
				statusEl.textContent = `Disease: ${data.disease}, Severity: ${data.severity}%, Action: ${data.action}`;
				setTimeout(() => window.location.reload(), 1000);
			} catch (e) {
				statusEl.textContent = 'Error during capture/detect.';
			} finally {
				btn.disabled = false;
			}
		});
	}

	// Video controls
	const startVideoBtn = document.getElementById('startVideoBtn');
	const stopVideoBtn = document.getElementById('stopVideoBtn');
	const toggleModeBtn = document.getElementById('toggleModeBtn');
	const detectionStatus = document.getElementById('detectionStatus');
	const leafResults = document.getElementById('leafResults');
	const videoFeed = document.getElementById('videoFeed');
	const modeIndicator = document.getElementById('modeIndicator');

	if (startVideoBtn) {
		startVideoBtn.addEventListener('click', async () => {
			detectionStatus.textContent = 'Starting video...';
			try {
				const res = await fetch('/api/start_video', { 
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ camera_index: 0 })
				});
				const data = await res.json();
				if (data.status === 'success') {
					detectionStatus.textContent = 'Video running - click on leaves to analyze them (manual mode)';
					startVideoBtn.disabled = true;
					stopVideoBtn.disabled = false;
					toggleModeBtn.disabled = false;
					// Enable video click handling
					enableVideoClickHandling();
					updateModeIndicator(false); // Start in manual mode
				} else {
					detectionStatus.textContent = 'Failed to start video: ' + data.message;
				}
			} catch (err) {
				detectionStatus.textContent = 'Error starting video: ' + err.message;
			}
		});
	}

	if (stopVideoBtn) {
		stopVideoBtn.addEventListener('click', async () => {
			detectionStatus.textContent = 'Stopping video...';
			try {
				const res = await fetch('/api/stop_video', { method: 'POST' });
				const data = await res.json();
				if (data.status === 'success') {
					detectionStatus.textContent = 'Video stopped';
					startVideoBtn.disabled = false;
					stopVideoBtn.disabled = true;
					toggleModeBtn.disabled = true;
					// Disable video click handling
					disableVideoClickHandling();
					// Clear results
					leafResults.innerHTML = '';
					updateModeIndicator(false);
				} else {
					detectionStatus.textContent = 'Failed to stop video: ' + data.message;
				}
			} catch (err) {
				detectionStatus.textContent = 'Error stopping video: ' + err.message;
			}
		});
	}

	if (toggleModeBtn) {
		toggleModeBtn.addEventListener('click', async () => {
			try {
				const res = await fetch('/api/toggle_automatic_mode', { method: 'POST' });
				const data = await res.json();
				if (data.status === 'success') {
					const isAutomatic = data.automatic_mode;
					updateModeIndicator(isAutomatic);
					
					if (isAutomatic) {
						detectionStatus.textContent = 'Automatic mode: Detecting leaves automatically every 3 seconds';
						disableVideoClickHandling();
						// Start automatic detection monitoring
						startAutomaticDetectionMonitoring();
					} else {
						detectionStatus.textContent = 'Manual mode: Click on leaves to analyze them';
						enableVideoClickHandling();
						stopAutomaticDetectionMonitoring();
					}
				} else {
					detectionStatus.textContent = 'Failed to toggle mode: ' + data.message;
				}
			} catch (err) {
				detectionStatus.textContent = 'Error toggling mode: ' + err.message;
			}
		});
	}

	// Initialize buttons
	if (stopVideoBtn) stopVideoBtn.disabled = true;
	if (toggleModeBtn) toggleModeBtn.disabled = true;

	let selectedRegions = [];
	let automaticDetectionInterval = null;

	function updateModeIndicator(isAutomatic) {
		if (modeIndicator) {
			modeIndicator.textContent = isAutomatic ? 'AUTOMATIC' : 'MANUAL';
			modeIndicator.className = isAutomatic ? 'mode-indicator automatic' : 'mode-indicator manual';
		}
	}

	function startAutomaticDetectionMonitoring() {
		// Poll for automatic detection results every 2 seconds
		automaticDetectionInterval = setInterval(async () => {
			try {
				const res = await fetch('/api/get_automatic_detections');
				if (res.ok) {
					const data = await res.json();
					if (data.status === 'success' && data.detections.length > 0) {
						showAutomaticDetectionResults(data.detections);
					}
				}
			} catch (err) {
				console.log('Error checking automatic detections:', err);
			}
		}, 2000);
	}

	function stopAutomaticDetectionMonitoring() {
		if (automaticDetectionInterval) {
			clearInterval(automaticDetectionInterval);
			automaticDetectionInterval = null;
		}
	}

	function showAutomaticDetectionResults(detections) {
		if (detections.length === 0) return;
		
		leafResults.innerHTML = '<h4>Automatic Detection Results:</h4>';
		
		detections.forEach((detection, index) => {
			const resultDiv = document.createElement('div');
			resultDiv.className = 'leaf-result automatic';
			
			if (detection.error) {
				resultDiv.innerHTML = `
					<strong>Leaf ${index + 1}</strong><br>
					<span class="error">Error: ${detection.error}</span><br>
					Confidence: ${(detection.confidence * 100).toFixed(1)}%
				`;
			} else {
				const diseaseClass = detection.class || 'unknown';
				resultDiv.innerHTML = `
					<strong>Leaf ${index + 1}</strong><br>
					<strong class="${diseaseClass}">${diseaseClass.toUpperCase()}</strong><br>
					Disease: ${detection.disease}<br>
					Severity: ${detection.severity.toFixed(1)}%<br>
					Confidence: ${(detection.confidence * 100).toFixed(1)}%
				`;
				resultDiv.className = `leaf-result automatic ${diseaseClass}`;
			}
			
			leafResults.appendChild(resultDiv);
		});
	}

	function enableVideoClickHandling() {
		if (videoFeed) {
			videoFeed.style.cursor = 'crosshair';
			videoFeed.addEventListener('click', handleVideoClick);
		}
	}

	function disableVideoClickHandling() {
		if (videoFeed) {
			videoFeed.style.cursor = 'default';
			videoFeed.removeEventListener('click', handleVideoClick);
		}
	}

	async function handleVideoClick(event) {
		const rect = videoFeed.getBoundingClientRect();
		const x = Math.round((event.clientX - rect.left) * (640 / rect.width));
		const y = Math.round((event.clientY - rect.top) * (480 / rect.height));
		
		try {
			const res = await fetch('/api/video_click', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ x, y })
			});
			
			const data = await res.json();
			if (data.status === 'success') {
				selectedRegions.push(data.region);
				detectionStatus.textContent = `Region ${data.region_count} created! Click "Analyze Region" to detect disease.`;
				showRegionSelection();
			} else {
				detectionStatus.textContent = 'Click failed: ' + data.error;
			}
		} catch (err) {
			detectionStatus.textContent = 'Error creating region: ' + err.message;
		}
	}

	function showRegionSelection() {
		if (selectedRegions.length === 0) return;
		
		leafResults.innerHTML = '<h4>Selected Regions:</h4>';
		
		selectedRegions.forEach((region, index) => {
			const regionDiv = document.createElement('div');
			regionDiv.className = 'leaf-result';
			regionDiv.innerHTML = `
				<strong>Region ${index + 1}</strong><br>
				<button onclick="analyzeRegion(${index})" class="analyze-btn">Analyze Region</button>
			`;
			leafResults.appendChild(regionDiv);
		});
	}

	// Make analyzeRegion function global
	window.analyzeRegion = async function(regionIndex) {
		try {
			detectionStatus.textContent = `Analyzing region ${regionIndex + 1}...`;
			
			const res = await fetch('/api/detect_leaf', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ region_index: regionIndex })
			});
			
			const data = await res.json();
			if (data.error) {
				detectionStatus.textContent = 'Analysis failed: ' + data.error;
			} else {
				detectionStatus.textContent = `Region ${regionIndex + 1} analyzed successfully!`;
				showAnalysisResult(regionIndex, data);
			}
		} catch (err) {
			detectionStatus.textContent = 'Error analyzing region: ' + err.message;
		}
	};

	function showAnalysisResult(regionIndex, result) {
		const regionDiv = leafResults.children[regionIndex + 1]; // +1 for the header
		if (regionDiv) {
			regionDiv.innerHTML = `
				<strong>Region ${regionIndex + 1}</strong><br>
				<strong class="${result.class}">${result.class.toUpperCase()}</strong><br>
				Disease: ${result.disease}<br>
				Severity: ${result.severity.toFixed(1)}%
			`;
			regionDiv.className = `leaf-result ${result.class}`;
		}
	}
}); 