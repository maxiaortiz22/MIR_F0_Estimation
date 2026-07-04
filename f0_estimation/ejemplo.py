import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

def autocorrelacion(señal):
    """
    Compute the autocorrelation of a signal.
    
    Parameters:
    -----------
    señal : array
        Input signal
        
    Returns:
    --------
    autocorr : array
        Normalized autocorrelation of the signal
    lags : array
        Corresponding lags
    """
    n = len(señal)
    # Normalize the signal (remove mean)
    señal_norm = señal - np.mean(señal)
    
    # Compute autocorrelation using numpy
    autocorr = np.correlate(señal_norm, señal_norm, mode='full')
    
    # Normalize by lag=0 value so the maximum is 1
    autocorr = autocorr / autocorr[n-1]
    
    # Keep only the right half (positive lags and zero)
    autocorr = autocorr[n-1:]
    
    # Create lags array
    lags = np.arange(0, n)
    
    return autocorr, lags


def detectar_frecuencia(autocorr, lags, freq_muestreo):
    """
    Detect the dominant frequency of a signal from its autocorrelation.
    
    Parameters:
    -----------
    autocorr : array
        Signal autocorrelation
    lags : array
        Corresponding lags
    freq_muestreo : float
        Sampling frequency in Hz
        
    Returns:
    --------
    frecuencia : float
        Dominant frequency in Hz
    periodo_muestras : int
        Period in number of samples
    """
    # Find peaks in autocorrelation (ignoring the first at lag=0)
    picos, _ = find_peaks(autocorr[1:], height=0.3)  # Adjust height as needed
    
    if len(picos) > 0:
        # The first peak corresponds to the fundamental period
        periodo_muestras = picos[0] + 1  # +1 because we start from lag=1
        frecuencia = freq_muestreo / periodo_muestras
        return frecuencia, periodo_muestras
    else:
        return None, None


# Example 1: Sinusoidal signal
t = np.linspace(0, 4, 400)
freq_muestreo = len(t) / (t[-1] - t[0])  # 100 samples/second

señal_sin = np.sin(2 * np.pi * 1 * t)  # 1 Hz sine wave

# Example 2: Signal with noise
señal_ruido = np.sin(2 * np.pi * 1 * t) + 0.5 * np.random.randn(len(t))

# Compute autocorrelation
autocorr_sin, lags_sin = autocorrelacion(señal_sin)
autocorr_ruido, lags_ruido = autocorrelacion(señal_ruido)

# Detect frequencies
freq_sin, periodo_sin = detectar_frecuencia(autocorr_sin, lags_sin, freq_muestreo)
freq_ruido, periodo_ruido = detectar_frecuencia(autocorr_ruido, lags_ruido, freq_muestreo)

print(f"Frecuencia de muestreo: {freq_muestreo:.2f} Hz")
print(f"\nSeñal sinusoidal:")
print(f"  - Período detectado: {periodo_sin} muestras ({periodo_sin/freq_muestreo:.3f} segundos)")
print(f"  - Frecuencia detectada: {freq_sin:.3f} Hz")
print(f"\nSeñal con ruido:")
print(f"  - Período detectado: {periodo_ruido} muestras ({periodo_ruido/freq_muestreo:.3f} segundos)")
print(f"  - Frecuencia detectada: {freq_ruido:.3f} Hz")

# Create figure with subplots
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Subplot 1: Original sinusoidal signal
axes[0, 0].plot(t, señal_sin, 'b-', linewidth=1.5)
axes[0, 0].set_xlabel('Time (s)')
axes[0, 0].set_ylabel('Amplitude')
axes[0, 0].set_title('Original Sinusoidal Signal')
axes[0, 0].grid(True, alpha=0.3)

# Subplot 2: Autocorrelation of sinusoidal signal
axes[0, 1].plot(lags_sin, autocorr_sin, 'r-', linewidth=1.5)
# Mark detected peaks
picos_sin, _ = find_peaks(autocorr_sin[1:], height=0.3)
axes[0, 1].plot(picos_sin + 1, autocorr_sin[picos_sin + 1], 'go', markersize=8, label='Detected peaks')
axes[0, 1].set_xlabel('Lag (samples)')
axes[0, 1].set_ylabel('Autocorrelation')
axes[0, 1].set_title(f'Autocorrelation - Sinusoidal Signal\nDetected frequency: {freq_sin:.3f} Hz')
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].axhline(y=0, color='k', linestyle='--', linewidth=0.5)
axes[0, 1].legend()

# Subplot 3: Signal with noise
axes[1, 0].plot(t, señal_ruido, 'g-', linewidth=1, alpha=0.7)
axes[1, 0].set_xlabel('Time (s)')
axes[1, 0].set_ylabel('Amplitude')
axes[1, 0].set_title('Sinusoidal Signal + Noise')
axes[1, 0].grid(True, alpha=0.3)

# Subplot 4: Autocorrelation of signal with noise
axes[1, 1].plot(lags_ruido, autocorr_ruido, 'm-', linewidth=1.5)
# Mark detected peaks
picos_ruido, _ = find_peaks(autocorr_ruido[1:], height=0.3)
axes[1, 1].plot(picos_ruido + 1, autocorr_ruido[picos_ruido + 1], 'go', markersize=8, label='Detected peaks')
axes[1, 1].set_xlabel('Lag (samples)')
axes[1, 1].set_ylabel('Autocorrelation')
axes[1, 1].set_title(f'Autocorrelation - Signal with Noise\nDetected frequency: {freq_ruido:.3f} Hz')
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].axhline(y=0, color='k', linestyle='--', linewidth=0.5)
axes[1, 1].legend()

plt.tight_layout()
plt.show()


# Additional example: Use your own signal
# ---------------------------------------
# señal_personalizada = np.array([...])  # Your signal here
# autocorr_personal, lags_personal = autocorrelacion(señal_personalizada)
# 
# plt.figure(figsize=(12, 5))
# plt.subplot(1, 2, 1)
# plt.plot(señal_personalizada)
# plt.title('Original Signal')
# plt.xlabel('Sample')
# plt.ylabel('Amplitude')
# plt.grid(True)
# 
# plt.subplot(1, 2, 2)
# plt.plot(lags_personal, autocorr_personal)
# plt.title('Autocorrelation')
# plt.xlabel('Lag')
# plt.ylabel('Autocorrelation')
# plt.grid(True)
# plt.tight_layout()
# plt.show()