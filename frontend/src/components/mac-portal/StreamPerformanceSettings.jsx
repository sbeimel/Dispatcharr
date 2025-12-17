import React, { useState, useEffect } from 'react';
import { Card, Form, Slider, Switch, Divider, Alert, Space, Typography } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Text } = Typography;

const StreamPerformanceSettings = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [smartBufferEnabled, setSmartBufferEnabled] = useState(true);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/mac-portal/settings/');
      form.setFieldsValue({
        buffer_chunks: response.data.buffer_chunks || 10,
        health_check_timeout: response.data.health_check_timeout || 10,
        health_check_timeout_switching: response.data.health_check_timeout_switching || 15,
        smart_buffer_clear_enabled: response.data.smart_buffer_clear_enabled !== false,
        buffer_clear_on_codec_change: response.data.buffer_clear_on_codec_change !== false,
        buffer_clear_on_resolution_change: response.data.buffer_clear_on_resolution_change !== false,
      });
      setSmartBufferEnabled(response.data.smart_buffer_clear_enabled !== false);
    } catch (error) {
      console.error('Error loading settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async (values) => {
    try {
      setLoading(true);
      await axios.patch('/api/mac-portal/settings/', values);
      // Show success message
    } catch (error) {
      console.error('Error saving settings:', error);
      // Show error message
    } finally {
      setLoading(false);
    }
  };

  const bufferMarks = {
    4: '4 (Fast)',
    10: '10 (Balanced)',
    20: '20 (Stable)',
  };

  const healthCheckMarks = {
    5: '5s',
    10: '10s',
    30: '30s',
  };

  const healthCheckSwitchingMarks = {
    10: '10s',
    15: '15s',
    60: '60s',
  };

  return (
    <Card title="Stream Performance Settings" loading={loading}>
      <Form
        form={form}
        layout="vertical"
        onValuesChange={(changedValues, allValues) => {
          if ('smart_buffer_clear_enabled' in changedValues) {
            setSmartBufferEnabled(changedValues.smart_buffer_clear_enabled);
          }
          saveSettings(allValues);
        }}
      >
        <Alert
          message="Performance Tuning"
          description="Adjust these settings based on your network conditions and hardware capabilities."
          type="info"
          icon={<InfoCircleOutlined />}
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Title level={5}>Buffer Settings</Title>
        
        <Form.Item
          label="Buffer Size (Chunks)"
          name="buffer_chunks"
          help="Buffer size in chunks (4-20, ~250KB per chunk). Higher = more buffering, lower latency."
        >
          <Slider min={4} max={20} marks={bufferMarks} />
        </Form.Item>

        <Divider />

        <Title level={5}>Health Check Settings</Title>

        <Form.Item
          label="Health Check Timeout (seconds)"
          name="health_check_timeout"
          help="How long without data before stream is marked unhealthy (5-30s)"
        >
          <Slider min={5} max={30} marks={healthCheckMarks} />
        </Form.Item>

        <Form.Item
          label="Health Check Timeout During Switch (seconds)"
          name="health_check_timeout_switching"
          help="Timeout during stream switch - should be higher to allow FFmpeg startup (10-60s)"
        >
          <Slider min={10} max={60} marks={healthCheckSwitchingMarks} />
        </Form.Item>

        <Divider />

        <Title level={5}>Smart Buffer Clearing</Title>

        <Alert
          message="What is Smart Buffer Clearing?"
          description="When enabled, the buffer is only cleared when switching between streams with different codecs or resolutions. This provides seamless transitions when streams are compatible."
          type="info"
          icon={<InfoCircleOutlined />}
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Form.Item
          label="Enable Smart Buffer Clearing"
          name="smart_buffer_clear_enabled"
          valuePropName="checked"
          help="Only clear buffer when codec or resolution changes (recommended)"
        >
          <Switch />
        </Form.Item>

        {smartBufferEnabled && (
          <Space direction="vertical" style={{ width: '100%', marginLeft: 24 }}>
            <Form.Item
              label="Clear on Codec Change"
              name="buffer_clear_on_codec_change"
              valuePropName="checked"
              help="Clear buffer when codec changes (e.g., h264 → hevc)"
            >
              <Switch />
            </Form.Item>

            <Form.Item
              label="Clear on Resolution Change"
              name="buffer_clear_on_resolution_change"
              valuePropName="checked"
              help="Clear buffer when resolution changes (e.g., 720p → 1080p)"
            >
              <Switch />
            </Form.Item>
          </Space>
        )}

        <Divider />

        <Alert
          message="Recommended Settings"
          description={
            <div>
              <Text strong>Fast Network (Fiber, LAN):</Text>
              <br />
              Buffer: 6-8, Health Check: 7s, Switching: 12s
              <br />
              <br />
              <Text strong>Standard Network (DSL, Cable):</Text>
              <br />
              Buffer: 10, Health Check: 10s, Switching: 15s (Default)
              <br />
              <br />
              <Text strong>Slow Network (Mobile, Satellite):</Text>
              <br />
              Buffer: 15-20, Health Check: 20-30s, Switching: 30-60s
            </div>
          }
          type="success"
        />
      </Form>
    </Card>
  );
};

export default StreamPerformanceSettings;
