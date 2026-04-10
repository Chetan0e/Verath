const BASE_URL = "http://localhost:8000"; // Update with your server IP for mobile

export const askQuestion = async (q) => {
  try {
    const response = await fetch(`${BASE_URL}/query?q=${encodeURIComponent(q)}`);
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Error asking question:', error);
    return { answer: 'Sorry, I could not connect to your SecondBrain.', context: [] };
  }
};

export const getTimeline = async () => {
  try {
    const response = await fetch(`${BASE_URL}/timeline`);
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Error getting timeline:', error);
    return { timeline: [] };
  }
};

export const getSummary = async () => {
  try {
    const response = await fetch(`${BASE_URL}/summary`);
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Error getting summary:', error);
    return { summary: 'No summary available.' };
  }
};

export const startRecording = async (duration = 10) => {
  try {
    const response = await fetch(`${BASE_URL}/record`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ duration }),
    });
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Error recording:', error);
    return { error: 'Failed to record audio' };
  }
};

export const getInsights = async () => {
  try {
    const response = await fetch(`${BASE_URL}/insights`);
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Error getting insights:', error);
    return { insights: [] };
  }
};

export const trainSpeaker = async (name, text) => {
  try {
    const response = await fetch(`${BASE_URL}/speaker/train`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, text }),
    });
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Error training speaker:', error);
    return { error: 'Failed to train speaker' };
  }
};

export const getVoiceProfiles = async () => {
  try {
    const response = await fetch(`${BASE_URL}/speaker/profiles`);
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Error getting voice profiles:', error);
    return { profiles: [] };
  }
};
