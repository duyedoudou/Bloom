import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getCourses, createCourse, deleteCourse, getGlobalStats,
  getSettings, updateSettings, testSettings, shutdownBloom,
} from '../lib/api';

export default function DashboardPage() {
  const [courses, setCourses] = useState([]);
  const [stats, setStats] = useState(null);
  const [newCourseName, setNewCourseName] = useState('');
  const [newCourseRef, setNewCourseRef] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState(null);
  const [settingsForm, setSettingsForm] = useState({ llm_api_key: '', llm_base_url: '', llm_model: '' });
  const [settingsStatus, setSettingsStatus] = useState('');
  const [savingSettings, setSavingSettings] = useState(false);
  const [testingSettings, setTestingSettings] = useState(false);
  const [exited, setExited] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([getCourses(), getGlobalStats()])
      .then(([c, s]) => { setCourses(c); setStats(s); })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const openSettings = async () => {
    setShowSettings(true);
    setSettingsStatus('');
    try {
      const data = await getSettings();
      setSettings(data);
      setSettingsForm({
        llm_api_key: '',
        llm_base_url: data.llm_base_url || '',
        llm_model: data.llm_model || '',
      });
    } catch (err) {
      setSettingsStatus(err.message);
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setSavingSettings(true);
    setSettingsStatus('');
    try {
      const payload = {
        llm_api_key: settingsForm.llm_api_key.trim() || null,
        llm_base_url: settingsForm.llm_base_url.trim(),
        llm_model: settingsForm.llm_model.trim(),
      };
      const data = await updateSettings(payload);
      setSettings(data);
      setSettingsForm((prev) => ({ ...prev, llm_api_key: '' }));
      setSettingsStatus('已保存并生效');
    } catch (err) {
      setSettingsStatus(err.message);
    } finally {
      setSavingSettings(false);
    }
  };

  const handleTestSettings = async () => {
    setTestingSettings(true);
    setSettingsStatus('');
    try {
      const result = await testSettings({
        llm_api_key: settingsForm.llm_api_key.trim() || null,
        llm_base_url: settingsForm.llm_base_url.trim() || null,
        llm_model: settingsForm.llm_model.trim() || null,
      });
      setSettingsStatus(result.ok ? `连接正常：${result.message}` : `连接失败：${result.message}`);
    } catch (err) {
      setSettingsStatus(err.message);
    } finally {
      setTestingSettings(false);
    }
  };

  const handleShutdown = async () => {
    if (!confirm('确定要退出 Bloom 吗？')) return;
    try {
      await shutdownBloom();
      setExited(true);
    } catch (err) {
      setError(err.message);
    }
  };

  if (exited) {
    return (
      <div className="min-h-[100dvh] bg-stone-50 flex items-center justify-center px-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-stone-900 mb-2">Bloom 已退出</h1>
          <p className="text-sm text-stone-400">可以关闭这个浏览器页面了。</p>
        </div>
      </div>
    );
  }

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newCourseName.trim() || creating) return;
    setError('');
    setCreating(true);
    try {
      const course = await createCourse(newCourseName.trim(), newCourseRef.trim());
      setCourses([course, ...courses]);
      setNewCourseName('');
      setNewCourseRef('');
      setShowCreate(false);
      navigate(`/course/${course.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (e, courseId) => {
    e.stopPropagation();
    if (!confirm('确定删除这个课程吗？所有课文和批注都将丢失。')) return;
    try {
      await deleteCourse(courseId);
      setCourses((prev) => prev.filter((c) => c.id !== courseId));
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-[100dvh] bg-stone-50">
      {/* Header — dark */}
      <header className="bg-stone-900 sticky top-0 z-10">
        <div className="max-w-[1100px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-base font-semibold text-white tracking-tight">Bloom</h1>
            <span className="text-stone-600 text-xs font-mono">2-Sigma Learning</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={openSettings}
              className="text-stone-400 hover:text-white text-sm transition-colors px-2 py-1"
            >
              设置
            </button>
            <button
              onClick={handleShutdown}
              className="text-stone-500 hover:text-rose-300 text-sm transition-colors px-2 py-1"
            >
              退出
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-[1100px] mx-auto px-6 py-10">
        {/* Page title + action */}
        <div className="flex items-end justify-between mb-8">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-stone-900">我的课程</h2>
            <p className="text-sm text-stone-400 mt-1">点击课程卡片进入学习</p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-emerald-700 transition-all duration-200 cursor-pointer"
          >
            新建课程
          </button>
        </div>

        {/* Learning Stats */}
        {stats && (stats.total_courses > 0) && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
            <div className="bg-white rounded-xl border border-stone-200/60 p-4">
              <p className="text-2xl font-semibold text-stone-900 tabular-nums">{stats.total_lessons_read}</p>
              <p className="text-xs text-stone-400 mt-1">已学课文</p>
            </div>
            <div className="bg-white rounded-xl border border-stone-200/60 p-4">
              <p className="text-2xl font-semibold text-stone-900 tabular-nums">{stats.total_annotations}</p>
              <p className="text-xs text-stone-400 mt-1">批注数</p>
            </div>
            <div className="bg-white rounded-xl border border-stone-200/60 p-4">
              <p className="text-2xl font-semibold text-stone-900 tabular-nums">{stats.current_streak}</p>
              <p className="text-xs text-stone-400 mt-1">连续学习天数</p>
            </div>
            <div className="bg-white rounded-xl border border-stone-200/60 p-4">
              <p className="text-2xl font-semibold text-emerald-600 tabular-nums">{stats.completed_courses}</p>
              <p className="text-xs text-stone-400 mt-1">已完成课程</p>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-rose-50 text-rose-600 text-sm px-4 py-2.5 rounded-lg mb-6 border border-rose-100">
            {error}
          </div>
        )}

        {/* Create form */}
        {showCreate && (
          <form onSubmit={handleCreate} className="mb-8 bg-white rounded-xl border border-stone-200/60 p-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1.5">课题名称</label>
              <input
                type="text"
                value={newCourseName}
                onChange={(e) => setNewCourseName(e.target.value)}
                placeholder="例如「博弈论基础」「Python 装饰器」"
                className="w-full px-3.5 py-2.5 bg-white border border-stone-200 rounded-lg text-sm transition-colors hover:border-stone-300 focus:border-emerald-600 outline-none"
                autoFocus
                disabled={creating}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1.5">
                参考材料
                <span className="text-stone-400 font-normal ml-1">（可选）</span>
              </label>
              <textarea
                value={newCourseRef}
                onChange={(e) => setNewCourseRef(e.target.value)}
                placeholder="粘贴课本章节、论文摘要、笔记、或任何你希望 AI 参考的内容..."
                className="w-full border border-stone-200 rounded-lg p-3.5 text-sm resize-none h-28 transition-colors hover:border-stone-300 focus:border-emerald-600 outline-none"
                disabled={creating}
              />
              <p className="text-xs text-stone-400 mt-1">AI 会根据这些材料设计课程大纲和课文内容</p>
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={creating}
                className="bg-stone-900 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-stone-800 disabled:opacity-50 transition-all duration-200 cursor-pointer"
              >
                {creating ? '创建中...' : '创建课程'}
              </button>
            </div>
          </form>
        )}

        {/* Course list */}
        {loading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="bg-white rounded-xl border border-stone-200/60 p-5">
                <div className="flex items-center justify-between">
                  <div className="skeleton h-4 rounded w-1/3" />
                  <div className="flex items-center gap-3">
                    <div className="skeleton h-5 rounded-full w-14" />
                    <div className="skeleton h-3 rounded w-8" />
                  </div>
                </div>
                <div className="skeleton h-3 rounded w-20 mt-2" />
              </div>
            ))}
          </div>
        ) : courses.length === 0 ? (
          <div className="py-20 text-center">
            <div className="w-12 h-12 rounded-full bg-stone-100 mx-auto mb-4 flex items-center justify-center">
              <svg className="w-5 h-5 text-stone-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
              </svg>
            </div>
            <p className="text-stone-400 text-sm mb-1">还没有课程</p>
            <p className="text-stone-300 text-xs">点击「新建课程」开始你的第一次一对一学习</p>
          </div>
        ) : (
          <div className="space-y-2">
            {courses.map((course, i) => (
              <div
                key={course.id}
                style={{ '--i': i }}
                className="stagger-in w-full bg-white rounded-xl p-5 text-left border border-stone-200/60 hover:border-stone-300 hover:shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] transition-all duration-200 group cursor-pointer"
                onClick={() => navigate(`/course/${course.id}`)}
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-stone-800 group-hover:text-stone-900 transition-colors">
                    {course.name}
                  </h3>
                  <div className="flex items-center gap-3">
                    {course.status === 'completed' ? (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-100">
                        已完成
                      </span>
                    ) : (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-stone-50 text-stone-500 border border-stone-100">
                        {Math.round(course.mastery_progress * 100)}%
                      </span>
                    )}
                    <span className="text-xs text-stone-400 font-mono tabular-nums">
                      {course.lesson_count} 篇
                    </span>
                    <button
                      onClick={(e) => handleDelete(e, course.id)}
                      className="opacity-0 group-hover:opacity-100 text-stone-300 hover:text-rose-500 transition-all p-1"
                      title="删除课程"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                      </svg>
                    </button>
                    <svg className="w-4 h-4 text-stone-300 group-hover:text-stone-500 group-hover:translate-x-0.5 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                    </svg>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-1.5">
                  <p className="text-xs text-stone-400 font-mono tabular-nums">
                    {new Date(course.created_at).toLocaleDateString('zh-CN')}
                  </p>
                  {course.status !== 'completed' && course.mastery_progress > 0 && (
                    <div className="flex-1 h-1 bg-stone-100 rounded-full overflow-hidden max-w-[120px]">
                      <div
                        className="h-full bg-emerald-500 rounded-full"
                        style={{ width: `${Math.round(course.mastery_progress * 100)}%` }}
                      />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {showSettings && (
        <div className="fixed inset-0 bg-stone-950/30 modal-backdrop flex items-center justify-center z-50 p-6">
          <form onSubmit={handleSaveSettings} className="bg-white rounded-2xl p-6 max-w-lg w-full shadow-[0_20px_40px_-15px_rgba(0,0,0,0.16)] border border-stone-200/60">
            <div className="flex items-start justify-between gap-4 mb-5">
              <div>
                <h3 className="font-semibold text-stone-900">AI 设置</h3>
                <p className="text-xs text-stone-400 mt-1">保存后立即生效，不需要重启 Bloom。</p>
              </div>
              <button
                type="button"
                onClick={() => setShowSettings(false)}
                className="text-stone-300 hover:text-stone-600 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">API Key</label>
                <input
                  type="password"
                  value={settingsForm.llm_api_key}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, llm_api_key: e.target.value }))}
                  placeholder={settings?.has_api_key ? `已配置：${settings.api_key_masked}，留空则不修改` : '请输入 API Key'}
                  className="w-full px-3.5 py-2.5 bg-white border border-stone-200 rounded-lg text-sm transition-colors hover:border-stone-300 focus:border-emerald-600 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">Base URL</label>
                <input
                  type="text"
                  value={settingsForm.llm_base_url}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, llm_base_url: e.target.value }))}
                  placeholder="https://api.moleapi.com/v1"
                  className="w-full px-3.5 py-2.5 bg-white border border-stone-200 rounded-lg text-sm transition-colors hover:border-stone-300 focus:border-emerald-600 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">Model</label>
                <input
                  type="text"
                  value={settingsForm.llm_model}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, llm_model: e.target.value }))}
                  placeholder="gpt-5.4-mini"
                  className="w-full px-3.5 py-2.5 bg-white border border-stone-200 rounded-lg text-sm transition-colors hover:border-stone-300 focus:border-emerald-600 outline-none"
                />
              </div>
            </div>

            {settingsStatus && (
              <div className="mt-4 text-sm text-stone-600 bg-stone-50 border border-stone-100 rounded-lg px-3 py-2 break-words">
                {settingsStatus}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 mt-6">
              <button
                type="button"
                onClick={handleTestSettings}
                disabled={testingSettings || savingSettings}
                className="px-4 py-2 text-sm bg-stone-100 text-stone-600 rounded-lg hover:bg-stone-200 disabled:opacity-50 transition-all cursor-pointer"
              >
                {testingSettings ? '测试中...' : '测试连接'}
              </button>
              <button
                type="submit"
                disabled={savingSettings || testingSettings}
                className="px-5 py-2 text-sm bg-stone-900 text-white rounded-lg hover:bg-stone-800 disabled:opacity-50 transition-all cursor-pointer"
              >
                {savingSettings ? '保存中...' : '保存设置'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
